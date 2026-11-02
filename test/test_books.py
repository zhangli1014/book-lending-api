import os
import time
import uuid

import pytest

TOKEN_TTL = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))

