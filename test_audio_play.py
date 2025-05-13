import os
import sys
import requests

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the speech generation function
from sabik_agent.tools.generate_speech_audio import generate_speech_audio

# Create a simple config class
class Config:
    REFERRER_ID = 'test'

# Enable auto-play
os.environ['TTS_AUTO_PLAY'] = 'true'

# Create a session
session = requests.Session()

# Test the speech generation with auto-play
result = generate_speech_audio(
    'This is a test of the auto-play functionality. The audio should play automatically.',
    voice='alloy',
    session=session,
    client=None,
    config=Config
)

print("\nResult:", result)