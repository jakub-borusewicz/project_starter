
test:
    copier copy --data project_name=dummy_project . . --trust

clear:
    rm -rf dummy_project
self_regenerate:
    copier copy --data project_name=project_starter . .. --trust