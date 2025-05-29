from collections import defaultdict
import time

MEDIA_GROUP_TIMEOUT_SEC = 2.0
pending_media_groups = defaultdict(list)
media_group_timestamps = {}
