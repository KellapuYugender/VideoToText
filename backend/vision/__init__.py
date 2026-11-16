"""Real-time vision pipeline: OpenCV capture + YOLO detection/tracking.

Kept free of Django imports so it can run standalone (``python -m vision.live``)
and be reused by the streaming consumer.
"""

import truststore

# Verify HTTPS (model weight downloads) against the OS certificate store, which
# also works behind antivirus/proxy TLS interception.
truststore.inject_into_ssl()
