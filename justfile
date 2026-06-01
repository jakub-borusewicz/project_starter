
dummy_project_name := "dummy_project"

[working-directory: "dummy_project"]
test:
    copier copy --data project_name={{dummy_project_name}} {{justfile_directory()}} . --trust


clear:
    rm -rf {{dummy_project_name}}
    mkdir {{dummy_project_name}}

self_regenerate:
    copier copy --data project_name=project_starter . .. --trust