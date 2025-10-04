"""
Twitter Agent - Refactored for AgentOSX Framework

Automated Twitter bot for posting tweets and converting blog posts to threads.
Migrated from agentOS with improved architecture and streaming support.
"""

import asyncio
import os
import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from agentosx.agents.base import BaseAgent, ExecutionContext
from agentosx.agents.decorators import agent, tool, streaming
from agentosx.streaming.events import (
    TextEvent, AgentStartEvent, AgentCompleteEvent,
    ToolCallEvent, ErrorEvent
)

# Import Twitter SDK components (from original agent)
try:
    import tweepy
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    tweepy = None
    Observer = None
    FileSystemEventHandler = None


logger = logging.getLogger(__name__)


@agent(
    name="twitter-agent",
    version="2.0.0",
    description="Automated Twitter bot with blog-to-thread conversion"
)
class TwitterAgent(BaseAgent):
    """
    Twitter automation agent with comprehensive features:
    - Post individual tweets
    - Create and post threads
    - Convert blog posts to Twitter threads using AI
    - Monitor blog directories for new posts
    - Track engagement analytics
    """
    
    def __init__(self):
        """Initialize Twitter agent."""
        super().__init__()
        self.name = "twitter-agent"
        self.version = "2.0.0"
        self.description = "Twitter automation agent"
        
        # Twitter API credentials
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        # Gemini API for thread generation
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Initialize Twitter clients
        self.api_v1 = None
        self.api_v2 = None
        self.client = None
        self._initialize_twitter_api()
        
        # Blog monitoring
        self.blog_observer = None
        self.blog_path = os.getenv('BLOG_POSTS_PATH')
        
        # Statistics
        self.tweets_posted = 0
        self.threads_posted = 0
        self.errors = 0
    
    def _initialize_twitter_api(self):
        """Initialize Twitter API clients."""
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            logger.warning("Twitter API credentials not fully configured")
            return
        
        try:
            # OAuth 1.0a for v1.1 API
            auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
            auth.set_access_token(self.access_token, self.access_token_secret)
            self.api_v1 = tweepy.API(auth)
            
            # OAuth 2.0 for v2 API
            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret
            )
            
            logger.info("Twitter API initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter API: {e}")
    
    # =========================================================================
    # Lifecycle Hooks
    # =========================================================================
    
    async def on_init(self):
        """Initialize agent."""
        logger.info("Twitter agent initialized")
        if not self.client:
            logger.warning("Twitter API not available - check credentials")
    
    async def on_start(self):
        """Start agent."""
        logger.info("Twitter agent started")
    
    async def on_stop(self):
        """Stop agent and cleanup."""
        logger.info(f"Twitter agent stopping - Posted {self.tweets_posted} tweets, {self.threads_posted} threads")
        if self.blog_observer:
            self.blog_observer.stop()
            self.blog_observer.join()
    
    # =========================================================================
    # Core Processing
    # =========================================================================
    
    async def process(self, input: str, context: ExecutionContext = None) -> str:
        """
        Process commands.
        
        Args:
            input: Command string
            context: Execution context
            
        Returns:
            Response string
        """
        if context:
            self.set_context(context)
        
        input_lower = input.lower()
        
        try:
            # Command routing
            if "post tweet" in input_lower or "tweet " in input_lower:
                text = input.replace("post tweet", "").replace("tweet", "").strip()
                result = await self.post_tweet(text)
                return f"Tweet posted successfully! {result.get('url', '')}"
            
            elif "post thread" in input_lower or "create thread" in input_lower:
                # Extract blog path from input or use default
                return await self._handle_thread_command(input)
            
            elif "timeline" in input_lower:
                timeline = await self.get_timeline(count=10)
                return f"Recent tweets:\n" + "\n".join([f"- {t}" for t in timeline[:5]])
            
            elif "monitor blog" in input_lower:
                if self.blog_path:
                    await self.start_blog_monitor()
                    return f"Started monitoring blog directory: {self.blog_path}"
                return "Error: BLOG_POSTS_PATH not configured"
            
            elif "stop monitor" in input_lower:
                await self.stop_blog_monitor()
                return "Stopped blog monitoring"
            
            elif "status" in input_lower:
                return self._get_status()
            
            else:
                return (
                    "Twitter Agent Commands:\n"
                    "- 'tweet [text]' - Post a tweet\n"
                    "- 'post thread' - Create thread from latest blog\n"
                    "- 'timeline' - View recent tweets\n"
                    "- 'monitor blog' - Start blog monitoring\n"
                    "- 'status' - Agent status\n"
                )
        
        except Exception as e:
            self.errors += 1
            logger.error(f"Error processing command: {e}")
            return f"Error: {str(e)}"
    
    # =========================================================================
    # Streaming Support
    # =========================================================================
    
    @streaming
    async def stream(self, input: str, context: ExecutionContext = None):
        """Stream progress updates."""
        yield AgentStartEvent(agent_id=self.name, data={"input": input})
        
        try:
            if "thread" in input.lower():
                yield TextEvent(agent_id=self.name, data="📝 Reading blog post...")
                await asyncio.sleep(0.5)
                
                yield TextEvent(agent_id=self.name, data="\n🤖 Generating thread with AI...")
                await asyncio.sleep(1.0)
                
                yield TextEvent(agent_id=self.name, data="\n✅ Thread generated! Posting to Twitter...")
                
                # Actual processing
                result = await self.process(input, context)
                
                yield TextEvent(agent_id=self.name, data=f"\n\n{result}")
                yield AgentCompleteEvent(
                    agent_id=self.name,
                    data={"status": "completed", "threads_posted": self.threads_posted}
                )
            else:
                result = await self.process(input, context)
                yield TextEvent(agent_id=self.name, data=result)
                yield AgentCompleteEvent(agent_id=self.name, data={"status": "completed"})
        
        except Exception as e:
            yield ErrorEvent(agent_id=self.name, data={"error": str(e)})
    
    # =========================================================================
    # Tools
    # =========================================================================
    
    @tool(
        name="post_tweet",
        description="Post a single tweet",
        schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "maxLength": 280},
                "media_urls": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["text"]
        }
    )
    async def post_tweet(self, text: str, media_urls: List[str] = None) -> Dict[str, Any]:
        """Post a single tweet."""
        if not self.client:
            raise ValueError("Twitter API not initialized")
        
        if len(text) > 280:
            raise ValueError(f"Tweet too long: {len(text)} characters (max 280)")
        
        try:
            response = self.client.create_tweet(text=text)
            self.tweets_posted += 1
            
            tweet_id = response.data['id']
            username = self.client.get_me().data.username
            
            return {
                "success": True,
                "tweet_id": tweet_id,
                "url": f"https://twitter.com/{username}/status/{tweet_id}",
                "text": text
            }
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            raise
    
    @tool(
        name="post_thread",
        description="Post a thread of tweets",
        schema={
            "type": "object",
            "properties": {
                "tweets": {"type": "array", "items": {"type": "string"}},
                "blog_title": {"type": "string"}
            },
            "required": ["tweets"]
        }
    )
    async def post_thread(self, tweets: List[str], blog_title: str = "Thread") -> Dict[str, Any]:
        """Post a thread of tweets."""
        if not self.client:
            raise ValueError("Twitter API not initialized")
        
        if not tweets:
            raise ValueError("No tweets provided")
        
        try:
            # Post first tweet
            response = self.client.create_tweet(text=tweets[0])
            first_tweet_id = response.data['id']
            previous_tweet_id = first_tweet_id
            
            logger.info(f"Posted main tweet (1/{len(tweets)})")
            
            # Post replies
            for i, tweet in enumerate(tweets[1:], 2):
                await asyncio.sleep(3)  # Rate limiting
                
                response = self.client.create_tweet(
                    text=tweet,
                    in_reply_to_tweet_id=previous_tweet_id
                )
                previous_tweet_id = response.data['id']
                logger.info(f"Posted reply {i}/{len(tweets)}")
            
            self.threads_posted += 1
            username = self.client.get_me().data.username
            thread_url = f"https://twitter.com/{username}/status/{first_tweet_id}"
            
            return {
                "success": True,
                "thread_url": thread_url,
                "tweet_count": len(tweets),
                "blog_title": blog_title
            }
        
        except Exception as e:
            logger.error(f"Failed to post thread: {e}")
            raise
    
    @tool(name="generate_thread", description="Generate thread from blog content")
    async def generate_thread(
        self,
        blog_content: str,
        blog_title: str,
        num_tweets: int = 5
    ) -> List[str]:
        """Generate a Twitter thread from blog content using Gemini."""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-pro')
            
            prompt = f"""
            Create a Twitter thread from this blog post. Generate {num_tweets} tweets.
            
            Blog Title: {blog_title}
            
            Blog Content:
            {blog_content[:6000]}  # Limit content length
            
            Guidelines:
            1. Create {num_tweets} tweets
            2. First tweet should be attention-grabbing with the topic
            3. Each tweet under 280 characters
            4. Include relevant hashtags (not too many)
            5. Last tweet should have a call to action
            6. Make it conversational and engaging
            
            Format: Return just the tweets, numbered 1., 2., etc.
            """
            
            response = model.generate_content(prompt)
            text = response.text
            
            # Parse tweets
            tweets = []
            for line in text.split('\n'):
                line = line.strip()
                if line and any(line.startswith(f"{i}.") for i in range(1, 20)):
                    tweet = line.split('.', 1)[1].strip()
                    if tweet:
                        tweets.append(tweet[:280])  # Ensure length limit
            
            return tweets[:num_tweets]
        
        except Exception as e:
            logger.error(f"Failed to generate thread: {e}")
            raise
    
    @tool(name="get_timeline", description="Get recent tweets")
    async def get_timeline(self, count: int = 10) -> List[str]:
        """Get recent tweets from timeline."""
        if not self.api_v1:
            raise ValueError("Twitter API v1 not initialized")
        
        try:
            tweets = self.api_v1.home_timeline(count=count)
            return [tweet.text for tweet in tweets]
        except Exception as e:
            logger.error(f"Failed to get timeline: {e}")
            raise
    
    @tool(name="analyze_engagement", description="Analyze tweet engagement")
    async def analyze_engagement(self, tweet_ids: List[str]) -> Dict[str, Any]:
        """Analyze engagement metrics for tweets."""
        if not self.client:
            raise ValueError("Twitter API not initialized")
        
        # Mock implementation - would need Twitter API premium/enterprise
        return {
            "analyzed_tweets": len(tweet_ids),
            "total_likes": 0,
            "total_retweets": 0,
            "total_replies": 0,
            "note": "Requires Twitter API Premium for full analytics"
        }
    
    # =========================================================================
    # Blog Monitoring
    # =========================================================================
    
    async def start_blog_monitor(self):
        """Start monitoring blog directory."""
        if not self.blog_path or not os.path.exists(self.blog_path):
            raise ValueError(f"Invalid blog path: {self.blog_path}")
        
        if Observer is None:
            raise ImportError("watchdog package required for blog monitoring")
        
        class BlogHandler(FileSystemEventHandler):
            def __init__(self, agent):
                self.agent = agent
            
            def on_created(self, event):
                if not event.is_directory and event.src_path.endswith('.md'):
                    asyncio.create_task(self.agent._process_new_blog(event.src_path))
        
        self.blog_observer = Observer()
        self.blog_observer.schedule(BlogHandler(self), self.blog_path, recursive=False)
        self.blog_observer.start()
        
        logger.info(f"Started monitoring: {self.blog_path}")
    
    async def stop_blog_monitor(self):
        """Stop blog monitoring."""
        if self.blog_observer:
            self.blog_observer.stop()
            self.blog_observer.join()
            self.blog_observer = None
            logger.info("Stopped blog monitoring")
    
    async def _process_new_blog(self, file_path: str):
        """Process a new blog post."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract title from frontmatter or filename
            title = Path(file_path).stem.replace('-', ' ').title()
            
            # Generate and post thread
            tweets = await self.generate_thread(content, title, num_tweets=5)
            result = await self.post_thread(tweets, title)
            
            logger.info(f"Posted thread for new blog: {title}")
            logger.info(f"Thread URL: {result['thread_url']}")
        
        except Exception as e:
            logger.error(f"Error processing new blog: {e}")
    
    async def _handle_thread_command(self, input: str) -> str:
        """Handle thread creation command."""
        if not self.blog_path:
            return "Error: BLOG_POSTS_PATH not configured"
        
        # Find latest blog post
        blog_files = list(Path(self.blog_path).glob("*.md"))
        if not blog_files:
            return "Error: No blog posts found"
        
        latest_blog = max(blog_files, key=lambda p: p.stat().st_ctime)
        
        with open(latest_blog, 'r', encoding='utf-8') as f:
            content = f.read()
        
        title = latest_blog.stem.replace('-', ' ').title()
        
        # Generate thread
        tweets = await self.generate_thread(content, title)
        
        # Post thread
        result = await self.post_thread(tweets, title)
        
        return (
            f"✅ Thread posted successfully!\n"
            f"Blog: {title}\n"
            f"Tweets: {result['tweet_count']}\n"
            f"URL: {result['thread_url']}"
        )
    
    def _get_status(self) -> str:
        """Get agent status."""
        return (
            f"Twitter Agent Status:\n"
            f"- API Connected: {'Yes' if self.client else 'No'}\n"
            f"- Tweets Posted: {self.tweets_posted}\n"
            f"- Threads Posted: {self.threads_posted}\n"
            f"- Errors: {self.errors}\n"
            f"- Blog Monitor: {'Running' if self.blog_observer else 'Stopped'}\n"
            f"- Blog Path: {self.blog_path or 'Not configured'}"
        )


# Example usage
async def main():
    """Example usage."""
    agent = TwitterAgent()
    await agent.initialize()
    await agent.start()
    
    # Check status
    status = await agent.process("status")
    print(status)
    
    # Example: Post a tweet (requires valid credentials)
    # response = await agent.process("tweet Hello from AgentOSX!")
    # print(response)
    
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
