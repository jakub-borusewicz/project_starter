package project_tools
//import L "list"
//import S "strings"
import (
	"tool/cli"
//		"tool/os"
//	"tool/exec"
		"tool/file"
)

//pre_commit_input: [string, ...] @tag(pre_commit_input)
pre_commit_input: string @tag(pre_commit_input)
command: {
	cue_auto_export: {
//		pre_commit_input: [string, ...] @tag(pre_commit_input)

		write_output: file.Create & {
			filename: "cue_tool_log.txt"
			contents: "\(pre_commit_input)"

		}
		print: cli.Print & {
			text: "Running cue-auto-export with input: \(pre_commit_input)"
//			text: "Running cue-auto-export with input: \(S.Join(pre_commit_input, " "))"
		}
	}
}