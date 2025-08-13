# Copyright 2025 Alejandro Martínez Corriá and the Thinkube contributors
# SPDX-License-Identifier: Apache-2.0

"""
WebSocket endpoint for streaming Ansible playbook execution
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any
import asyncio
import logging
import os
import json
import yaml
import tempfile
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter(tags=["playbook-stream"])


@router.websocket("/ws/playbook/{playbook_name:path}")
async def stream_playbook_execution(websocket: WebSocket, playbook_name: str):
    """Stream Ansible playbook execution output via WebSocket"""
    from urllib.parse import unquote
    
    await websocket.accept()
    logger.info(f"WebSocket accepted for playbook: {playbook_name}")
    
    try:
        # Decode the URL-encoded playbook name
        playbook_name = unquote(playbook_name)
        logger.info(f"Decoded playbook name: {playbook_name}")
        
        # Receive execution parameters
        logger.info("Waiting to receive parameters from WebSocket...")
        try:
            # Add a timeout to prevent hanging
            data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
            logger.info(f"Received parameters: {list(data.keys())}")
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for WebSocket parameters")
            await websocket.send_json({
                "type": "error",
                "message": "Timeout waiting for execution parameters"
            })
            return
        except Exception as e:
            logger.error(f"Error receiving parameters: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"Error receiving parameters: {str(e)}"
            })
            return
        
        # Extract dynamic inventory if provided
        dynamic_inventory = data.get("inventory", None)
        
        # Handle both short names and full paths
        playbook_mapping = {
            "setup-ssh-keys": "ansible/00_initial_setup/10_setup_ssh_keys.yaml",
            "test-ssh-connectivity": "ansible/00_initial_setup/18_test_ssh_connectivity.yaml",
            "microk8s-setup": "ansible/20_lxd_setup/20_deploy_microk8s.yaml",
            "keycloak-deploy": "ansible/40_thinkube/core/keycloak/10_deploy.yaml",
            "harbor-deploy": "ansible/40_thinkube/core/harbor/10_deploy.yaml"
        }
        
        # Check if it's a short name in the mapping
        if playbook_name in playbook_mapping:
            playbook_relative_path = playbook_mapping[playbook_name]
        # Check if it's already a path starting with 'ansible/'
        elif playbook_name.startswith('ansible/'):
            playbook_relative_path = playbook_name
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown playbook: {playbook_name}"
            })
            return
            
        # Build playbook path
        thinkube_root = Path.home() / "thinkube"
        playbook_path = thinkube_root / playbook_relative_path
        
        if not playbook_path.exists():
            await websocket.send_json({
                "type": "error",
                "message": f"Playbook not found: {playbook_path}"
            })
            return
            
        # Get parameters
        environment = data.get("environment", {})
        extra_vars = data.get("extra_vars", {})
        
        # Add venv Python to extra_vars BEFORE writing to file
        # EXCEPT for the SSH setup playbook that needs to install Python first
        initial_setup_playbooks = [
            "10_setup_ssh_keys.yaml"
        ]
        
        # Check if this is an initial setup playbook
        is_initial_setup = any(playbook in playbook_relative_path for playbook in initial_setup_playbooks)
        
        user_venv = Path.home() / ".venv"
        if user_venv.exists() and not is_initial_setup:
            venv_python = str(user_venv / "bin" / "python3")
            extra_vars['ansible_python_interpreter'] = venv_python
            logger.info(f"Using venv Python interpreter: {venv_python}")
        else:
            logger.info(f"Not setting Python interpreter for playbook: {playbook_relative_path}")
        
        # Build ansible-playbook command directly for better output control
        inventory_path = thinkube_root / "inventory" / "inventory.yaml"
        
        # Create a temporary vars file for authentication
        import tempfile
        temp_vars_fd, temp_vars_path = tempfile.mkstemp(suffix='.yml', prefix='ansible-vars-')
        try:
            with os.fdopen(temp_vars_fd, 'w') as f:
                import yaml
                yaml.dump(extra_vars, f)
        except:
            os.close(temp_vars_fd)
            raise
        
        # Update inventory file if dynamic inventory provided
        if dynamic_inventory:
            # The installer saves to the main inventory.yaml
            # Just ensure it has proper formatting
            try:
                # Ensure dynamic inventory ends with newline
                if not dynamic_inventory.endswith('\n'):
                    dynamic_inventory += '\n'
                    
                with open(inventory_path, 'w') as f:
                    f.write(dynamic_inventory)
                print(f"Updated inventory at {inventory_path}")
                    
            except Exception as e:
                print(f"Error saving inventory: {e}")
                raise
        
        # Always use the main inventory path
        inventory_to_use = str(inventory_path)
        
        # Find ansible-playbook in user venv or system
        ansible_playbook_path = "ansible-playbook"
        user_venv_ansible = Path.home() / ".venv" / "bin" / "ansible-playbook"
        if user_venv_ansible.exists():
            ansible_playbook_path = str(user_venv_ansible)
        
        # Build command to run ansible-playbook directly
        cmd = [
            "stdbuf", "-oL", "-eL",  # Force line buffering
            ansible_playbook_path,
            "-i", inventory_to_use,
            str(playbook_path),
            "-e", f"@{temp_vars_path}",
            "-v"  # Verbose output
        ]
            
        # Set up environment with Ansible specific settings for real-time output
        env = os.environ.copy()
        env.update(environment)
        
        # Add venv to PATH if it exists
        if user_venv.exists():
            venv_bin = str(user_venv / "bin")
            current_path = env.get('PATH', '')
            env['PATH'] = f"{venv_bin}:{current_path}"
        
        # Force unbuffered output and disable color codes
        env['PYTHONUNBUFFERED'] = '1'
        env['ANSIBLE_FORCE_COLOR'] = '0'  # Disable color codes for cleaner parsing
        env['ANSIBLE_STDOUT_CALLBACK'] = 'default'  # Use default callback for standard output
        env['ANSIBLE_HOST_KEY_CHECKING'] = 'False'
        env['ANSIBLE_CONFIG'] = str(thinkube_root / "ansible.cfg")
        
        # Send start message
        logger.info("Sending start message to WebSocket")
        await websocket.send_json({
            "type": "start",
            "message": "Starting playbook execution",
            "playbook": playbook_name
        })
        logger.info("Start message sent")
        
        # Create subprocess with unbuffered output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # Combine stderr into stdout
            env=env,
            cwd=str(thinkube_root),
            bufsize=0  # Unbuffered for real-time output
        )
        
        # Stream output line by line
        task_pattern = "TASK ["
        play_pattern = "PLAY ["
        ok_pattern = "ok: ["
        changed_pattern = "changed: ["
        failed_pattern = "failed: ["
        
        current_task = "Initializing"
        task_count = 0
        
        async def process_line(line_text):
            nonlocal current_task, task_count
            
            # Debug logging
            if line_text:
                logger.info(f"Ansible output: {line_text}")
            
            # Always send the line to frontend for visibility
            if line_text:  # Skip empty lines
                # Parse Ansible output for task information
                if task_pattern in line_text:
                    task_start = line_text.find(task_pattern) + len(task_pattern)
                    task_end = line_text.find("]", task_start)
                    if task_end > task_start:
                        current_task = line_text[task_start:task_end]
                        task_count += 1
                        
                        await websocket.send_json({
                            "type": "task",
                            "task_number": task_count,
                            "task_name": current_task,
                            "message": line_text
                        })
                elif play_pattern in line_text:
                    await websocket.send_json({
                        "type": "play",
                        "message": line_text
                    })
                elif ok_pattern in line_text:
                    await websocket.send_json({
                        "type": "ok",
                        "task": current_task,
                        "message": line_text
                    })
                elif changed_pattern in line_text:
                    await websocket.send_json({
                        "type": "changed",
                        "task": current_task,
                        "message": line_text
                    })
                elif failed_pattern in line_text:
                    await websocket.send_json({
                        "type": "failed",
                        "task": current_task,
                        "message": line_text
                    })
                else:
                    # Regular output
                    await websocket.send_json({
                        "type": "output",
                        "message": line_text
                    })
        
        async def read_stream():
            buffer = b''
            while True:
                try:
                    # Read in chunks to handle very long lines
                    chunk = await process.stdout.read(4096)
                    if not chunk:
                        # Process any remaining buffer
                        if buffer:
                            line_text = buffer.decode('utf-8', errors='replace').rstrip()
                            if line_text:
                                await process_line(line_text)
                        break
                    
                    buffer += chunk
                    
                    # Process complete lines from buffer
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        line_text = line.decode('utf-8', errors='replace').rstrip()
                        if line_text:
                            await process_line(line_text)
                        
                except Exception as e:
                    logger.error(f"Error reading stream: {e}")
                    break
        
        # Read output
        await read_stream()
        
        # Wait for process to complete
        return_code = await process.wait()
        
        # Send completion message
        if return_code == 0:
            await websocket.send_json({
                "type": "complete",
                "status": "success",
                "message": "Playbook completed successfully",
                "return_code": return_code
            })
        else:
            await websocket.send_json({
                "type": "complete",
                "status": "error",
                "message": "Playbook execution failed",
                "return_code": return_code
            })
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        if 'process' in locals() and process.returncode is None:
            process.terminate()
            await process.wait()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close()
    finally:
        # Clean up temp files
        if 'temp_vars_path' in locals():
            try:
                os.unlink(temp_vars_path)
            except:
                pass
        # Note: We intentionally keep installer-inventory.yaml for debugging
        # and to ensure it survives system restarts