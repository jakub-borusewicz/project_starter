package project_tools
//import L "list"
import S "strings"
//import Re "regexp"
import Tu "github.com/jakub-borusewicz/jacues/tools:tool_utils"
import "path"
import (
//	"tool/cli"
//		"tool/os"
	"tool/exec"
		"tool/file"
)


extension_out_map: {
    ".json": "json",
    ".cue": "cue",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".jsonl": "jsonl",
    ".ldjson": "jsonl",
    ".textproto": "textproto",
    ".proto": "proto",
    ".go": "go",
    ".txt": "text",
    "": "text",
}

//pre_commit_input: [string, ...] @tag(pre_commit_input)
cue_file_path: string @tag(cue_file_path)
command: {
	cue_auto_export: {
//		pre_commit_input: [string, ...] @tag(pre_commit_input)

		filepath_without_cue: S.TrimSuffix(cue_file_path, ".cue")
		file_extension: path.Ext(filepath_without_cue, path.Unix)
		out_param: extension_out_map[file_extension]

		run_cue_export: exec.Run & Tu.#shell & {
			_dep: file_extension
			expression: "cue export \(cue_file_path) --out \(out_param) --outfile \(filepath_without_cue) --force"
			stdout: string
		}


		output_content: out_param
		write_output: file.Append & {
			filename: "cue_tool_log.txt"
			contents: "\n\(output_content)"
		}
	}
}