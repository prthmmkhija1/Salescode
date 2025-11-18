"""
Test Suite for Filler Word Filter
Tests the intelligent filler detection system with various scenarios.

Run with: python examples/voice_agents/test_filler_filter.py
"""

import asyncio
import logging
import os
from typing import AsyncIterable

from dotenv import load_dotenv

# Load .env FIRST before any other imports that might use env vars
# Get absolute path to project root
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

# Test scenarios counter
test_results = {
    "filler_ignored": 0,
    "real_interruption": 0,
    "filler_when_quiet": 0,
    "mixed_content": 0,
}


class TestAgent(Agent):
    """Test agent with long responses to allow interruption testing."""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful voice assistant. "
                "When asked about weather, use the get_weather function. "
                "Answer questions naturally and conversationally. "
                "Keep your responses concise but friendly."
            ),
        )

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
        llm=groq.LLM(model="llama-3.3-70b-versatile"),  # Using Groq's current LLM
        stt=deepgram.STT(
            model="nova-2",
            language="en",
            # Enable interim results for better testing
            interim_results=True,
        ),
        tts=cartesia.TTS(
            voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # British Lady
        ),
        
        # ===== INTERRUPTION SETTINGS =====
        allow_interruptions=True,
        min_interruption_duration=0.3,  # Lower for faster testing
        min_interruption_words=1,  # Require at least 1 word to interrupt
        
        # ===== FALSE INTERRUPTION HANDLING =====
        resume_false_interruption=True,
        false_interruption_timeout=1.5,
        
        # ===== OTHER SETTINGS =====
        preemptive_generation=False,  # Disable for clearer testing
    )

    # Event handlers for monitoring
    @session.on("user_input_transcribed")
    def on_transcript(event):
        """Log all transcriptions for debugging."""
        if event.is_final:
            logger.info(f"📝 FINAL TRANSCRIPT: '{event.transcript}'")
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
    await session.start(agent=TestAgent(), room=ctx.room)
    
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
    logger.info("5️⃣  HINDI FILLERS (if applicable):")
    logger.info("   - While agent speaks, say: 'haan' or 'accha'")
    logger.info("   - Expected: Agent continues (Hindi filler ignored)")
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
            "Greet the user warmly and tell them you're ready to help test "
            "the filler word detection system. Mention that they can ask you "
            "to tell a story or count numbers to test interruptions. "
            "Keep this greeting relatively short (about 10 seconds)."
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