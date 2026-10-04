// Copyright Alejandro Martínez Corriá and the Thinkube contributors
// SPDX-License-Identifier: Apache-2.0
//
// Written by Thinkube (ansible/roles/agent_clients); a configuration run
// replaces this file.
//
// Playwright's browser_take_screenshot returns the image only when it is
// called without a filename; with one it saves a file and returns its path, and
// the model never sees the page. The filename is removed, so every screenshot
// reaches the model as an image.

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
	pi.on("tool_call", async (event) => {
		if (event.toolName !== "mcp__playwright__browser_take_screenshot") return undefined;
		delete (event.input as { filename?: unknown }).filename;
		return undefined;
	});
}
