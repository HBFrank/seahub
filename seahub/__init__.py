# Copyright (c) 2012-2016 Seafile Ltd.
from signals import repo_created, repo_deleted, clean_up_repo_trash ,clean_up_repo_trash_item
from handlers import repo_created_cb, repo_deleted_cb, clean_up_repo_trash_cb, clean_up_repo_trash_item_cb

repo_created.connect(repo_created_cb)
repo_deleted.connect(repo_deleted_cb)
clean_up_repo_trash.connect(clean_up_repo_trash_cb)
clean_up_repo_trash_item.connect(clean_up_repo_trash_item_cb)

try:
    # ../conf/seahub_settings.py
    from seahub_settings import repo_created_callback
    repo_created.connect(repo_created_callback)
except ImportError:
    pass
