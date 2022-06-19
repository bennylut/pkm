import email.utils as eu

from datetime import datetime
from datetime import timezone

print(eu.parsedate_to_datetime(eu.format_datetime(datetime.now().astimezone(timezone.utc), True)))
