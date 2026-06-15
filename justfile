dummy_project_name := "dummy_project"

test: clear
    cd {{dummy_project_name}} && copier copy --data project_name={{dummy_project_name}} {{justfile_directory()}} . --trust


clear:
    rm -rf {{dummy_project_name}}
    mkdir {{dummy_project_name}}

self_regenerate:
    copier copy --data project_name=project_starter . . --trust


test_cue_auto_export:
    prek run cue-auto-export-tool --all-files

pre-commit:
    prek run --all-files
