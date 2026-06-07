dummy_project_name := "dummy_project"

test:
    mkdir {{dummy_project_name}}
    cd {{dummy_project_name}}
    copier copy --data project_name={{dummy_project_name}} {{justfile_directory()}} . --trust


clear:
    rm -rf {{dummy_project_name}}
    mkdir {{dummy_project_name}}

self_regenerate:
    copier copy --data project_name=project_starter . .. --trust