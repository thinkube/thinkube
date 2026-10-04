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

import type { Plugin } from "@opencode-ai/plugin";

export const ThinkubeScreenshot: Plugin = async () => ({
	"tool.execute.before": async (input, output) => {
		if (input.tool === "playwright_browser_take_screenshot") delete output.args.filename;
	},
});
