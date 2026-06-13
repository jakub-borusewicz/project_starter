package project_tools
//import L "list"
//import S "strings"
import (
//	"tool/cli"
//		"tool/os"
//	"tool/exec"
		"tool/file"
)

//pre_commit_input: [string, ...] @tag(pre_commit_input)
pre_commit_input: string @tag(pre_commit_input)
command: {
	cue_auto_export: {
//		pre_commit_input: [string, ...] @tag(pre_commit_input)

		write_output: file.Append & {
			filename: "cue_tool_log.txt"
			contents: "\n\(pre_commit_input)"

		}
	}
}