# Filler Word Filter & Multilingual Voice Agent

## Branch: `feature/livekit-interrupt-handler-Pratham`

This branch implements an intelligent filler word detection system with multilingual support (Hindi + English) for LiveKit voice agents. The system intelligently distinguishes between filler words (like "umm", "hmm", "haan", "accha") and genuine interruptions, preventing false interruptions while maintaining responsive stop command handling.

---

## What Changed

### New Modules Added

#### 1. **FillerWordFilter** (`livekit-agents/livekit/agents/voice/filler_filter.py`)

- Core module for intelligent filler word detection
- Supports 100+ filler words across 10 languages
- Methods:
  - `is_only_filler(text)` - Check if text contains only filler words
  - `contains_meaningful_content(text)` - Check if text has real content beyond fillers
  - `add_ignored_words(words)` - Dynamically add custom filler words at runtime

#### 2. **Test Agent** (`examples/voice_agents/test_filler_filter.py`)

- Comprehensive test suite for filler detection scenarios
- Multi-language voice agent with Hindi/English support
- Stop command detection (English + Hindi)
- Features:
  - Weather lookup function tool (`get_weather()`)
  - Automatic language matching (responds in same language as user input)
  - Stop command suppression (prevents agent from saying "OK" after stop commands)

### New Parameters & Configuration

**STT Configuration (Deepgram)**

```python
stt=deepgram.STT(
    model="nova-2",
    language="multi",  # Multilingual model for Hindi + English
    interim_results=True,
    punctuate=True,
    smart_format=True,
)
```

**TTS Configuration (Cartesia)**

```python
tts=cartesia.TTS(
    voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # British Lady voice
)
```

**LLM Configuration (Groq)**

```python
llm=groq.LLM(model="llama-3.1-8b-instant")  # Fast, efficient model
```

**Interruption Settings**

```python
allow_interruptions=True,
min_interruption_duration=0.5,  # Require 0.5s of speech to interrupt
min_interruption_words=1,       # Require at least 1 word
resume_false_interruption=True, # Resume speech if filler detected
false_interruption_timeout=2.0, # Wait 2s before considering it false
```

### Logic & Algorithms

**Filler Detection Algorithm**

1. Normalize text (lowercase, remove punctuation)
2. Split into words
3. Remove filler words from word list
4. Check if any meaningful words remain
5. If only fillers → ignore interruption
6. If meaningful content → allow interruption

**Stop Command Detection**

- Tracks stop words in both English and Hindi
- Suppresses auto-response after stop commands
- Prevents agent from saying "OK" acknowledgments

**Language Matching**

- LLM automatically detects user's language
- Responds in the same language as input
- Hindi input → Hindi response
- English input → English response

---

## What Works

### ✅ Verified Features (Manual Testing)

1. **Filler Word Detection (English)**

   - ✅ "umm", "hmm", "uh", "er", "like", "well" are ignored during agent speech
   - ✅ Agent continues speaking without interruption

2. **Filler Word Detection (Hindi)**

   - ✅ "haan", "accha", "theek", "arre", "ji", "matlab" are ignored
   - ✅ Agent continues speaking when user says Hindi fillers

3. **Real Interruptions**

   - ✅ "stop", "wait", "hold on", "enough" interrupt agent
   - ✅ Agent stops immediately and doesn't resume

4. **Hindi Stop Commands**

   - ✅ "chup", "shaant", "ruko", "khamosh" interrupt agent
   - ✅ Agent recognizes Hindi stop words as genuine interruptions

5. **Multilingual Support**

   - ✅ Deepgram "multi" language model transcribes Hindi and English
   - ✅ Agent responds in the same language as user input
   - ✅ Code-switching (Hinglish) is supported

6. **False Interruption Recovery**

   - ✅ When filler is detected, agent resumes speech after 2-second timeout
   - ✅ "FALSE INTERRUPTION DETECTED - Speech RESUMED" event fires

7. **LiveKit Cloud Integration**

   - ✅ Agent registers successfully with LiveKit Cloud
   - ✅ Room connections work properly
   - ✅ Audio streaming functional

8. **Dynamic Filler Word Updates**
   - ✅ `FillerWordFilter.add_ignored_words()` method available
   - ✅ Custom filler words can be added at runtime
   - ✅ Changes apply immediately to detection logic

---

## Known Issues

### ⚠️ Edge Cases & Instability

1. **IPC Watcher Error (Non-Critical)**

   - Error: `DuplexClosed` exception in dev mode
   - Impact: Doesn't affect agent functionality
   - Workaround: Ignore the error - agent still registers successfully

2. **Groq Rate Limits**

   - Daily token limit: 100,000 tokens for free tier
   - Model: `llama-3.1-8b-instant` used to reduce token consumption
   - Workaround: Use paid Groq API key or switch to smaller model

3. **Stop Command Acknowledgment**

   - Issue: Agent sometimes says "OK" after stop commands
   - Current Fix: `say()` override suppresses "ok", "okay", "sure", "alright"
   - Limitation: May suppress legitimate short responses

4. **Language Detection Accuracy**

   - Deepgram "multi" model may occasionally misidentify language
   - Hindi words sometimes transcribed phonetically in English
   - Workaround: Use clear pronunciation and avoid heavy accents

5. **Filler Word Ambiguity**
   - Some words can be fillers or meaningful (e.g., "bas" in Hindi)
   - Current: Removed ambiguous words from filler list
   - Trade-off: Some actual fillers may trigger interruptions

---

## Steps to Test

### Prerequisites

1. Python 3.9+
2. LiveKit Cloud account (or local LiveKit server)
3. API Keys:
   - Deepgram API key
   - Cartesia API key
   - Groq API key
   - LiveKit API key and secret

### Setup

1. **Clone & Install**

```bash
git clone <repository>
cd Salescode
git checkout feature/livekit-interrupt-handler-Pratham
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -e livekit-agents
pip install -e livekit-plugins/livekit-plugins-deepgram
pip install -e livekit-plugins/livekit-plugins-cartesia
pip install -e livekit-plugins/livekit-plugins-groq
pip install -e livekit-plugins/livekit-plugins-silero
```

2. **Configure Environment**
   Create `.env` file in project root:

```env
LIVEKIT_URL=wss://salescode-4rdih579.livekit.cloud
LIVEKIT_API_KEY=APIm7Ao49d3Mv4Q
LIVEKIT_API_SECRET=<your-secret>

DEEPGRAM_API_KEY=<your-deepgram-key>
CARTESIA_API_KEY=<your-cartesia-key>
GROQ_API_KEY=<your-groq-key>
```

3. **Run Agent**

```bash
.\venv\Scripts\python.exe examples\voice_agents\test_filler_filter.py dev
```

4. **Access LiveKit Playground**
   - Go to: https://cloud.livekit.io/projects/salescode-4rdih579/playground
   - Create a new room or join existing room
   - Agent will automatically join

### Test Scenarios

#### Test 1: Filler While Agent Speaks

1. Say: **"Tell me about the weather"**
2. While agent is speaking, say: **"umm"** or **"hmm"**
3. **Expected**: Agent continues speaking (filler ignored)
4. **Log**: `⚠️ FALSE INTERRUPTION DETECTED - Speech RESUMED`

#### Test 2: Real Interruption (English)

1. Say: **"Tell me about the weather"**
2. While agent is speaking, say: **"stop"** or **"wait"**
3. **Expected**: Agent stops immediately
4. **Log**: Agent state changes to `listening`

#### Test 3: Hindi Filler Words

1. Say: **"Mausam kaisa hai?"** (What's the weather?)
2. While agent responds in Hindi, say: **"haan"** or **"accha"**
3. **Expected**: Agent continues speaking in Hindi
4. **Log**: Filler ignored, no interruption

#### Test 4: Hindi Stop Commands

1. Say: **"Mausam ke baare mein batao"**
2. While agent speaks, say: **"chup"** or **"shaant"** or **"ruko"**
3. **Expected**: Agent stops immediately
4. **Log**: Stop command detected, agent stops

#### Test 5: Mixed Language (Code-Switching)

1. Say: **"Hello, Delhi ka weather batao"**
2. **Expected**: Agent understands and responds appropriately
3. Language detection should work for Hinglish

#### Test 6: Dynamic Filler Addition

```python
# In test_filler_filter.py or console
from livekit.agents.voice.filler_filter import FillerWordFilter

# Add custom fillers at runtime
FillerWordFilter.add_ignored_words(['basically', 'literally', 'actually'])

# Now "basically" will be ignored as a filler word
```

### Monitoring & Debugging

**Watch Logs For:**

- `📝 FINAL TRANSCRIPT:` - User speech transcription
- `🤖 Agent: listening → thinking` - Agent processing
- `👤 User: speaking → listening` - User speech detection
- `⚠️ FALSE INTERRUPTION DETECTED` - Filler word ignored
- `🛑 STOP COMMAND` - Stop word detected
- `🔇 Suppressing acknowledgment` - "OK" suppressed

**Test Summary (End of Session):**

```
📊 TEST SUMMARY
Fillers Ignored: 0
Real Interruptions: 0
Fillers When Quiet: 0
Mixed Content: 0
```

---

## Environment Details

### Python Version

- **Minimum**: Python 3.9
- **Tested**: Python 3.13
- **Recommended**: Python 3.11+

### Dependencies

**Core Libraries**

```
livekit-agents==1.3.2
livekit==1.0.19
python-dotenv==1.0.0
```

**Plugin Dependencies**

```
livekit-plugins-deepgram (nova-2 model)
livekit-plugins-cartesia (TTS)
livekit-plugins-groq (LLM)
livekit-plugins-silero (VAD)
```

**System Requirements**

- Windows 10/11, Linux, or macOS
- 4GB+ RAM
- Stable internet connection (for cloud STT/TTS/LLM)

### Configuration Instructions

#### Deepgram STT

- Model: `nova-2`
- Language: `multi` (supports Hindi, English, 40+ languages)
- Features: `interim_results`, `punctuate`, `smart_format`
- API: https://deepgram.com/

#### Cartesia TTS

- Voice ID: `79a125e8-cd45-4c13-8a67-188112f4dd22` (British Lady)
- Language Support: English, Hindi (via phonetic synthesis)
- API: https://cartesia.ai/

#### Groq LLM

- Model: `llama-3.1-8b-instant` (fast, efficient)
- Alternative: `llama-3.3-70b-versatile` (more capable, higher token usage)
- Free Tier: 100,000 tokens/day
- API: https://groq.com/

#### LiveKit Cloud

- Server: `wss://salescode-4rdih579.livekit.cloud`
- Region: India West
- Dashboard: https://cloud.livekit.io/

---

## Dynamic Filler Word Management

### Adding Custom Filler Words at Runtime

The `FillerWordFilter` class supports dynamic updates to the ignored word list:

```python
from livekit.agents.voice.filler_filter import FillerWordFilter

# Add custom filler words
FillerWordFilter.add_ignored_words([
    'basically',      # English filler
    'literally',      # English filler
    'dekho',          # Hindi - "look"
    'suno',           # Hindi - "listen"
    'yaar',           # Hindi/Urdu - "friend" (used as filler)
])
```

### Pre-Loaded Filler Words

**English** (50+ words)

- `uh`, `um`, `hmm`, `mm`, `mhm`, `ah`, `er`
- `like`, `well`, `you know`, `i mean`, `basically`
- All variations: `umm`, `ummm`, `hmmm`, `hmmmm`, etc.

**Hindi** (40+ words)

- `haan`, `accha`, `theek`, `arre`, `ji`, `vaise`
- `matlab`, `bilkul`, `sahi`, `huh`, `hmm`
- `achha`, `acha`, `thik`, `are`, `waise`

**Other Languages** (60+ words)

- Spanish: `eh`, `pues`, `este`, `bueno`
- French: `euh`, `ben`, `alors`, `voilà`
- German: `äh`, `ähm`, `also`, `na ja`
- Portuguese: `né`, `tipo`, `então`
- Chinese: `嗯` (en), `那个` (nàge), `就是` (jiùshì)
- Japanese: `あの` (ano), `えっと` (etto), `まあ` (maa)
- Arabic: `يعني` (ya'ni), `طيب` (tayyib)
- Korean: `음` (eum), `그` (geu), `뭐` (mwo)
- Russian: `ну` (nu), `вот` (vot), `это` (eto)

### Checking Current Filler List

```python
from livekit.agents.voice.filler_filter import FillerWordFilter

filter = FillerWordFilter()
print(filter._ignored_words)  # View all ignored words
```

---

## Architecture Overview

```
User Speech
    ↓
Deepgram STT (multi-language)
    ↓
Transcript → FillerWordFilter.is_only_filler()
    ↓
    ├─→ Only Filler? → Ignore Interruption → Agent Continues
    ↓
    └─→ Real Content? → Allow Interruption → Agent Stops
            ↓
        Groq LLM Processing
            ↓
        Language Matching (Hindi/English)
            ↓
        Cartesia TTS
            ↓
        Audio Output
```

---

## Future Enhancements

### Planned Features

1. **Confidence-Based Filtering**

   - Use STT confidence scores to validate filler detection
   - Threshold: confidence < 0.6 → likely filler

2. **Context-Aware Detection**

   - Track conversation context to identify fillers
   - Example: "hmm" while thinking vs. "hmm" as acknowledgment

3. **Machine Learning Classification**

   - Train model to classify filler vs. meaningful speech
   - Use audio features (pitch, duration, volume) as inputs

4. **User-Specific Filler Profiles**

   - Learn individual user's filler patterns
   - Adapt detection based on user behavior

5. **Real-Time Analytics Dashboard**
   - Visualize filler detection statistics
   - Monitor interruption patterns
   - Track language distribution

---

## Troubleshooting

### Agent Not Listening

- **Check**: Terminal output for transcripts (`📝 FINAL TRANSCRIPT:`)
- **Solution**: Verify Deepgram API key and `language="multi"`
- **Test**: Say "Hello" clearly and wait for transcript

### Hindi Not Recognized

- **Check**: STT language configuration (`language="multi"`)
- **Solution**: Ensure clear pronunciation, reduce background noise
- **Test**: Say "Namaste" - should transcribe as "Namaste"

### Stop Commands Not Working

- **Check**: Stop words list in `STOP_WORDS`
- **Solution**: Verify word is in list, add if missing
- **Test**: Say "stop" clearly - agent should stop immediately

### Agent Responds in Wrong Language

- **Check**: LLM instructions in `TestAgent.__init__()`
- **Solution**: Ensure "Reply in the SAME language" instruction is present
- **Test**: Say "Hello" (should get English), "Namaste" (should get Hindi)

### Rate Limit Errors

- **Check**: Groq API token usage in error message
- **Solution**: Use paid API key or switch to `llama-3.1-8b-instant`
- **Monitor**: Token usage in Groq dashboard

---

## Contributors

- **Pratham** - Filler filter implementation, multilingual support
- **LiveKit Team** - Core agent framework

## License

This project follows the same license as the main LiveKit Agents repository.

---

## Support

For issues or questions:

1. Check [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
2. Open an issue on GitHub
3. Join [LiveKit Slack Community](https://livekit.io/join-slack)
