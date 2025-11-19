
import asyncio
import logging
import os
from typing import AsyncIterable

from dotenv import load_dotenv

import pathlib
project_root = pathlib.Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=project_root / ".env", override=True)

from livekit import rtc
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, function_tool
from livekit.plugins import cartesia, deepgram, groq, silero

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("filler-filter-test")

test_results = {
    "filler_ignored": 0,
    "real_interruption": 0,
    "filler_when_quiet": 0,
    "mixed_content": 0,
}


class TestAgent(Agent):
    """Test agent that stays silent after stop commands."""
    
    # Words that should make agent completely silent (English + Hindi + Hinglish)
    STOP_WORDS = [
        # English
        'stop', 'wait', 'enough', 'quiet', 'silence', 'hold on', 'hold',
        # Hindi/Hinglish stop commands - specific phrases only
        'chup', 'choop', 'shaant', 'shant', 'khamosh',
        'ruko', 'rukho', 'ruk ja', 'ruk jao',
        'bas karo', 'band karo', 'mat bolo',
    ]
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful voice assistant. "
                "Reply in the SAME language as the user's input. "
                "If user speaks Hindi, respond in Hindi. If English, respond in English. "
                "Keep responses short, clear, and friendly. "
                "When interrupted, NEVER respond - just stay completely silent."
            ),
        )
    
    def say(self, text: str) -> None:
        """Override say to check for stop command responses."""
        # If the response is just acknowledging a stop command, suppress it
        if text.strip().lower() in ['ok', 'okay', 'sure', 'alright']:
            logger.info(f"🔇 Suppressing acknowledgment: '{text}'")
            return
        super().say(text)

    @function_tool
    async def get_weather(self, location: str = "New York") -> str:
        """Get weather information for testing."""
        logger.info(f"☀️ Getting weather for {location}")
        return f"The weather in {location} is sunny and pleasant, perfect for testing voice agents!"

    # Removed count_numbers tool due to schema issues with Groq


server = AgentServer()


def prewarm(proc):
    """Prewarm function to load VAD model."""
    logger.info("🔥 Prewarming VAD model...")
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("✅ VAD model loaded successfully")


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entrypoint for the test agent."""
    
    logger.info("=" * 80)
    logger.info("🚀 FILLER FILTER TEST AGENT STARTING")
    logger.info("=" * 80)
    
    # Create session with basic voice agent settings
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        llm=groq.LLM(
            model="llama-3.1-8b-instant",
            temperature=0.7,
        ),
        stt=deepgram.STT(
            model="nova-2",
            language="multi",  # Multi-language model - supports Hindi, English, and code-switching
            interim_results=True,
            punctuate=True,
            smart_format=True,
        ),
        tts=cartesia.TTS(
            voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # British Lady
        ),
        
        # ===== INTERRUPTION SETTINGS =====
        allow_interruptions=True,
        min_interruption_duration=0.5,  # Require at least 0.5 seconds of speech
        min_interruption_words=1,  # Require at least 1 word to interrupt
        
        # ===== FALSE INTERRUPTION HANDLING =====
        resume_false_interruption=True,
        false_interruption_timeout=2.0,  # Wait 2 seconds before considering it false
        
        # ===== OTHER SETTINGS =====
        preemptive_generation=False,  # Disable for clearer testing
        
        # ===== TURN DETECTION =====
        # This prevents auto-response after every user utterance
        # turn_detection=None,  # Disable automatic turn detection to prevent auto-response
    )

    # Event handlers for monitoring
    # Track stop commands to prevent auto-response (English + Hindi)
    stop_words = [
        'stop', 'wait', 'enough', 'quiet', 'silence', 'hold',
        'chup', 'choop', 'shaant', 'shant', 'khamosh',
        'ruko', 'rukho', 'ruk ja', 'bas karo', 'band karo', 'mat bolo'
    ]
    last_was_stop_command = False
    
    @session.on("user_input_transcribed")
    def on_transcript(event):
        """Log all transcriptions for debugging."""
        nonlocal last_was_stop_command
        if event.is_final:
            logger.info(f"📝 FINAL TRANSCRIPT: '{event.transcript}'")
            # Check if this was a stop command
            transcript_lower = event.transcript.lower().strip()
            last_was_stop_command = any(word in transcript_lower for word in stop_words)
            if last_was_stop_command:
                logger.info("🛑 STOP COMMAND DETECTED - Agent will stay silent")
        else:
            logger.debug(f"📝 Interim: '{event.transcript}'")

    @session.on("agent_state_changed")
    def on_agent_state(event):
        """Log agent state changes."""
        logger.info(f"🤖 Agent: {event.old_state} → {event.new_state}")

    @session.on("user_state_changed")
    def on_user_state(event):
        """Log user state changes."""
        logger.info(f"👤 User: {event.old_state} → {event.new_state}")

    @session.on("agent_false_interruption")
    def on_false_interruption(event):
        """Log false interruptions."""
        if event.resumed:
            logger.info("⚠️  FALSE INTERRUPTION DETECTED - Speech RESUMED")
            test_results["filler_ignored"] += 1
        else:
            logger.info("⚠️  FALSE INTERRUPTION DETECTED - Speech STOPPED")

    @session.on("speech_created")
    def on_speech_created(event):
        """Log when speech is created."""
        logger.info(f"🗣️  Speech created: {event.source} (interruptions: {event.speech_handle.allow_interruptions})")

    # Start the session
    agent = TestAgent()
    await session.start(agent=agent, room=ctx.room)
    
    # Send initial greeting through the session
    await asyncio.sleep(1)  # Wait for session to be ready
    session.say("Hello! How can I assist you today?")
    
    # Print welcome message with test instructions
    logger.info("\n" + "=" * 80)
    logger.info("🎯 FILLER FILTER TEST SCENARIOS")
    logger.info("=" * 80)
    logger.info("\n📋 Test the following scenarios:\n")
    logger.info("1️⃣  FILLER WHILE AGENT SPEAKS:")
    logger.info("   - Say: 'tell me a long story'")
    logger.info("   - While agent is speaking, say: 'umm' or 'hmm'")
    logger.info("   - Expected: Agent continues speaking (filler ignored)")
    logger.info("")
    logger.info("2️⃣  REAL INTERRUPTION:")
    logger.info("   - Say: 'tell me a long story'")
    logger.info("   - While agent is speaking, say: 'wait stop' or 'hold on'")
    logger.info("   - Expected: Agent stops immediately")
    logger.info("")
    logger.info("3️⃣  FILLER WHEN QUIET:")
    logger.info("   - Wait for agent to finish")
    logger.info("   - Say: 'umm'")
    logger.info("   - Expected: System registers it as speech")
    logger.info("")
    logger.info("4️⃣  MIXED FILLER AND COMMAND:")
    logger.info("   - Say: 'count numbers for me'")
    logger.info("   - While agent is speaking, say: 'umm okay stop'")
    logger.info("   - Expected: Agent stops (contains valid command)")
    logger.info("")
    logger.info("5️⃣  HINDI SUPPORT:")
    logger.info("   - Try speaking in Hindi: 'mausam kaisa hai?'")
    logger.info("   - Expected: Agent responds in Hindi")
    logger.info("")
    logger.info("6️⃣  HINDI FILLERS:")
    logger.info("   - While agent speaks, say: 'haan', 'accha', 'theek', 'matlab'")
    logger.info("   - Expected: Agent continues (Hindi filler ignored)")
    logger.info("")
    logger.info("7️⃣  MIXED LANGUAGE (Code-switching):")
    logger.info("   - Say: 'hello, mausam batao Delhi ka'")
    logger.info("   - Expected: Agent understands and responds appropriately")
    logger.info("")
    logger.info("=" * 80)
    logger.info("💡 Tips:")
    logger.info("   - Watch the logs to see filler detection in action")
    logger.info("   - Look for 'Ignoring filler-only interruption' messages")
    logger.info("   - Check if FALSE INTERRUPTION events are triggered")
    logger.info("=" * 80 + "\n")
    
    # Generate initial greeting
    session.generate_reply(
        instructions=(
            "Say: 'Hello! How can I assist you today?'"
        )
    )
    
    # Optional: Dynamically update filler words during runtime
    # Uncomment to test runtime updates
    # await asyncio.sleep(10)
    # if session.options.filler_filter:
    #     logger.info("🔄 Dynamically adding 'okay' to filler list")
    #     session.options.filler_filter.add_ignored_words(["okay", "alright"])


def print_test_summary():
    """Print test summary on shutdown."""
    logger.info("\n" + "=" * 80)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Fillers Ignored: {test_results['filler_ignored']}")
    logger.info(f"Real Interruptions: {test_results['real_interruption']}")
    logger.info(f"Fillers When Quiet: {test_results['filler_when_quiet']}")
    logger.info(f"Mixed Content: {test_results['mixed_content']}")
    logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        cli.run_app(server)
    finally:
        print_test_summary()