from __future__ import annotations

import logging

logger = logging.getLogger("svoydom")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
