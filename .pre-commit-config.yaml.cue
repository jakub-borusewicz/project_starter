import "list"

import pre_commit "github.com/jakub-borusewicz/jacues/pre_commit:pre_commit"

pre_commit

#cue_auto_export_hook: {
	id:   "cue-auto-export-tool"
	name: "cue-auto-export-tool"
	entry: """
		bash -c 'for f in "$@"; do cue cmd cue_auto_export -t cue_file_path="$f"; done' --
		"""
	language:       "system"
	pass_filenames: true
	files:          ".*\\.cue$"
	exclude:        "(?x)^(config/.* | cue.mod/.* | .*_tool.cue | template/.*)$"
}
#local_repo: pre_commit.#Repo & {
	hooks: [...pre_commit.#Hook]
}

//#local_repo: pre_commit.repos[4]
#local_repo: pre_commit.repos[3] & {
	hooks: list.Concat([pre_commit.repos[3].hooks, [#cue_auto_export_hook]])
}

repos: list.Concat([pre_commit.repos, [#local_repo]])
