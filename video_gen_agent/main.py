"""
Main entry point for the Video Generation Agent.
Provides CLI interface for video generation and rating.
"""

import asyncio
import argparse
import sys
from pathlib import Path

from video_gen_agent.config import config
from video_gen_agent.agents.orchestrator import VideoGenerationAgent, run_video_generation
from video_gen_agent.memory.database import VideoGenDatabase
from video_gen_agent.memory.learning import LearningSystem


def validate_config():
    """Validate configuration before running."""
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease configure your .env file. Copy .env.example to .env and add your API keys.")
        return False
    return True


async def generate_video_cli(
    topic: str,
    output: str,
    format: str,
    mode: str = "single"
):
    """Run video generation from CLI."""
    print(f"\n🎬 Starting video generation...")
    print(f"   Topic: {topic}")
    print(f"   Format: {format}")
    print(f"   Mode: {mode}")
    print(f"   Output: {output}")
    print()
    
    agent = VideoGenerationAgent(mode=mode)
    
    try:
        result = await agent.generate(
            topic_or_script=topic,
            output_name=output,
            video_format=format
        )
        
        if result["status"] == "completed":
            print("\n✅ Video generation completed!")
            
            if result.get("final_video_path"):
                print(f"   Output: {result['final_video_path']}")
                
                # Save to database
                db = VideoGenDatabase()
                gen_id = db.save_generation(
                    topic=topic,
                    script="",  # Could extract from messages
                    video_format=format,
                    output_path=result['final_video_path'],
                    duration=0,
                    media_sources=[]
                )
                print(f"   Generation ID: {gen_id} (use for rating)")
            else:
                print("   Note: Video path not found in response")
                if result.get("messages"):
                    print("\n   Agent messages:")
                    for msg in result["messages"][-3:]:  # Last 3 messages
                        print(f"   > {msg[:200]}...")
        else:
            print(f"\n❌ Generation failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise


def rate_video_cli(
    generation_id: int,
    overall: int,
    script: int = None,
    visuals: int = None,
    audio: int = None,
    pacing: int = None,
    feedback: str = None
):
    """Rate a generated video."""
    db = VideoGenDatabase()
    
    # Verify generation exists
    gen = db.get_generation(generation_id)
    if not gen:
        print(f"❌ Generation ID {generation_id} not found")
        return
    
    # Save rating
    rating_id = db.save_rating(
        generation_id=generation_id,
        overall_score=overall,
        script_score=script,
        visuals_score=visuals,
        audio_score=audio,
        pacing_score=pacing,
        feedback=feedback
    )
    
    print(f"✅ Rating saved (ID: {rating_id})")
    print(f"   Overall: {overall}/5")
    if script:
        print(f"   Script: {script}/5")
    if visuals:
        print(f"   Visuals: {visuals}/5")
    if audio:
        print(f"   Audio: {audio}/5")
    if pacing:
        print(f"   Pacing: {pacing}/5")
    
    # Analyze learnings
    learning = LearningSystem(db)
    summary = learning.get_learning_summary()
    
    if summary["learned_preferences"]:
        print("\n📚 Updated learned preferences:")
        for pref in summary["learned_preferences"]:
            print(f"   - {pref['preference']}")


def show_history_cli(limit: int = 10):
    """Show recent generation history."""
    db = VideoGenDatabase()
    generations = db.get_recent_generations(limit)
    
    if not generations:
        print("No generations found.")
        return
    
    print(f"\n📜 Recent Generations (last {limit}):\n")
    
    for gen in generations:
        rating = gen.get('avg_rating')
        rating_str = f"★ {rating:.1f}" if rating else "Not rated"
        
        print(f"  [{gen['id']}] {gen['topic'][:50]}...")
        print(f"      Format: {gen['video_format']} | {rating_str}")
        print(f"      Created: {gen['created_at']}")
        print()


def show_learnings_cli():
    """Show what the agent has learned."""
    learning = LearningSystem()
    summary = learning.get_learning_summary()
    
    print("\n🧠 Learning Summary:\n")
    print(f"   Total rated generations: {summary['total_generations_rated']}")
    
    if summary["category_performance"]:
        print("\n   Category Performance:")
        for cat, perf in summary["category_performance"].items():
            status_emoji = "✅" if perf["status"] == "good" else "⚠️"
            print(f"      {status_emoji} {cat.title()}: {perf['average']}/5")
    
    if summary["learned_preferences"]:
        print("\n   Learned Preferences:")
        for pref in summary["learned_preferences"]:
            print(f"      - {pref['type']}: {pref['preference']} (confidence: {pref['confidence']})")
    
    if summary["improvement_areas"]:
        print("\n   Areas for Improvement:")
        for area in summary["improvement_areas"]:
            print(f"      - {area.title()}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Video Generation Agent - Create videos from topics using AI"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate a video")
    gen_parser.add_argument(
        "--topic", "-t",
        required=True,
        help="Video topic or script"
    )
    gen_parser.add_argument(
        "--output", "-o",
        default="generated_video",
        help="Output file name (without extension)"
    )
    gen_parser.add_argument(
        "--format", "-f",
        choices=["horizontal", "vertical"],
        default="horizontal",
        help="Video format: horizontal (16:9) or vertical (9:16)"
    )
    gen_parser.add_argument(
        "--mode", "-m",
        choices=["single", "sequential"],
        default="single",
        help="Agent mode: 'single' (one orchestrator) or 'sequential' (multi-agent pipeline)"
    )
    
    # Rate command
    rate_parser = subparsers.add_parser("rate", help="Rate a generated video")
    rate_parser.add_argument(
        "--id", "-i",
        type=int,
        required=True,
        help="Generation ID to rate"
    )
    rate_parser.add_argument(
        "--overall", "-o",
        type=int,
        required=True,
        choices=[1, 2, 3, 4, 5],
        help="Overall rating (1-5)"
    )
    rate_parser.add_argument("--script", type=int, choices=[1, 2, 3, 4, 5])
    rate_parser.add_argument("--visuals", type=int, choices=[1, 2, 3, 4, 5])
    rate_parser.add_argument("--audio", type=int, choices=[1, 2, 3, 4, 5])
    rate_parser.add_argument("--pacing", type=int, choices=[1, 2, 3, 4, 5])
    rate_parser.add_argument("--feedback", type=str, help="Optional text feedback")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show generation history")
    history_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Number of entries to show"
    )
    
    # Learnings command
    subparsers.add_parser("learnings", help="Show learned preferences")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        if not validate_config():
            sys.exit(1)
        asyncio.run(generate_video_cli(args.topic, args.output, args.format, args.mode))
        
    elif args.command == "rate":
        rate_video_cli(
            generation_id=args.id,
            overall=args.overall,
            script=args.script,
            visuals=args.visuals,
            audio=args.audio,
            pacing=args.pacing,
            feedback=args.feedback
        )
        
    elif args.command == "history":
        show_history_cli(args.limit)
        
    elif args.command == "learnings":
        show_learnings_cli()
        
    else:
        parser.print_help()


# Also export for programmatic use
async def generate_video(
    topic: str,
    output_name: str = "generated_video",
    video_format: str = "horizontal"
) -> dict:
    """
    Generate a video programmatically.
    
    Args:
        topic: Video topic or script
        output_name: Output file name
        video_format: 'horizontal' or 'vertical'
    
    Returns:
        Generation result dict
    """
    return await run_video_generation(topic, output_name, video_format)


if __name__ == "__main__":
    main()
