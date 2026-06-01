
[working-directory: "dummy_project"]
test:
    copier copy --data project_name=dummy_project {{justfile_directory()}} . --trust


clear:
    rm -rf dummy_project
    mkdir dummy_project

self_regenerate:
    copier copy --data project_name=project_starter . .. --trust