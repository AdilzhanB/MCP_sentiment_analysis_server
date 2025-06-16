import json
import gradio as gr
from textblob import TextBlob
from typing import Dict, Any, List
import asyncio

class SentimentMCPServer:
    """MCP Server for Sentiment Analysis using TextBlob"""
    
    def __init__(self):
        self.name = "sentiment-analyzer"
        self.version = "1.0.0"
    
    async def get_tools(self) -> List[Dict]:
        """Returns the list of tools available in this MCP"""
        return [
            {
                "name": "analyze_sentiment",
                "description": "Analyze the sentiment of text using TextBlob NLP",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to analyze for sentiment"
                        },
                        "detailed": {
                            "type": "boolean",
                            "description": "Return detailed analysis including confidence and statistics",
                            "default": False
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "batch_analyze",
                "description": "Analyze sentiment for multiple texts at once",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "texts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of texts to analyze"
                        }
                    },
                    "required": ["texts"]
                }
            },
            {
                "name": "sentiment_summary",
                "description": "Get summary statistics for analyzed texts",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "texts": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "required": ["texts"]
                }
            }
        ]
    
    async def call_tool(self, name: str, arguments: Dict) -> Dict:
        """Call the specified tool with the given arguments."""
        if name == "analyze_sentiment":
            return await self.analyze_sentiment(
                arguments["text"], 
                arguments.get("detailed", False)
            )
        elif name == "batch_analyze":
            return await self.batch_analyze(arguments["texts"])
        elif name == "sentiment_summary":
            return await self.sentiment_summary(arguments["texts"])
        else:
            raise ValueError(f"Unknown tool: {name}")

    async def analyze_sentiment(self, text: str, detailed: bool = False) -> Dict[str, Any]:
        """Main sentiment analysis function"""
        if not text or not text.strip():
            return {"error": "Text cannot be empty"}
        
        blob = TextBlob(text)
        sentiment = blob.sentiment
        
        # Base analysis result
        result = {
            "text": text[:100] + "..." if len(text) > 100 else text,
            "polarity": round(sentiment.polarity, 3),
            "subjectivity": round(sentiment.subjectivity, 3),
            "assessment": self._get_assessment(sentiment.polarity)
        }
        
        # Detailed analysis
        if detailed:
            result.update({
                "confidence": self._get_confidence(sentiment.polarity),
                "word_count": len(text.split()),
                "character_count": len(text),
                "interpretation": self._get_interpretation(sentiment)
            })
        
        return result
    
    async def batch_analyze(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze sentiment for multiple texts"""
        results = []
        for i, text in enumerate(texts):
            try:
                result = await self.analyze_sentiment(text, detailed=True)
                result["index"] = i
                results.append(result)
            except Exception as e:
                results.append({"index": i, "error": str(e), "text": text})
        
        return {"results": results, "total_analyzed": len(texts)}
    
    async def sentiment_summary(self, texts: List[str]) -> Dict[str, Any]:
        """Generate summary statistics for a batch of texts"""
        batch_result = await self.batch_analyze(texts)
        results = batch_result["results"]
        
        # Фильтруем успешные результаты
        valid_results = [r for r in results if "error" not in r]
        
        if not valid_results:
            return {"error": "No valid results to summarize"}
        
        polarities = [r["polarity"] for r in valid_results]
        assessments = [r["assessment"] for r in valid_results]
        
        # Подсчет по категориям
        positive = sum(1 for a in assessments if a == "positive")
        negative = sum(1 for a in assessments if a == "negative")
        neutral = sum(1 for a in assessments if a == "neutral")
        
        return {
            "total_texts": len(texts),
            "analyzed": len(valid_results),
            "average_polarity": round(sum(polarities) / len(polarities), 3),
            "sentiment_distribution": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral
            },
            "percentages": {
                "positive": round(positive / len(valid_results) * 100, 1),
                "negative": round(negative / len(valid_results) * 100, 1),
                "neutral": round(neutral / len(valid_results) * 100, 1)
            }
        }
    
    def _get_assessment(self, polarity: float) -> str:
        """Sentiment assessment based on polarity"""
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    
    def _get_confidence(self, polarity: float) -> str:
        """Confidence level based on polarity"""
        abs_polarity = abs(polarity)
        if abs_polarity >= 0.7:
            return "high"
        elif abs_polarity >= 0.3:
            return "medium"
        else:
            return "low"
    
    def _get_interpretation(self, sentiment) -> str:
        """Reult interpretation based on sentiment analysis"""
        polarity = sentiment.polarity
        subjectivity = sentiment.subjectivity
        
        if subjectivity > 0.7:
            subj_desc = "highly subjective (opinion-based)"
        elif subjectivity > 0.3:
            subj_desc = "moderately subjective"
        else:
            subj_desc = "objective (fact-based)"
        
        if abs(polarity) > 0.5:
            pol_desc = "strong sentiment"
        elif abs(polarity) > 0.2:
            pol_desc = "moderate sentiment"
        else:
            pol_desc = "neutral sentiment"
        
        return f"This text shows {pol_desc} and is {subj_desc}."

# Global instance of the MCP server
mcp_server = SentimentMCPServer()

def sentiment_analysis(text: str) -> Dict[str, Any]:
    """Wrapper for Gradio interface to call MCP server"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            mcp_server.analyze_sentiment(text, detailed=True)
        )
        return result
    finally:
        loop.close()

def format_results(result: Dict[str, Any]) -> str:
    """Format the results for display in Gradio"""
    if "error" in result:
        return f"❌ **Error:** {result['error']}"
    
    emoji_map = {"positive": "😊", "negative": "😞", "neutral": "😐"}
    polarity_color = "🟢" if result["polarity"] > 0 else "🔴" if result["polarity"] < 0 else "🟡"
    
    return f"""
## 📊 MCP Sentiment Analysis Results

### {emoji_map[result['assessment']]} Assessment: **{result['assessment'].title()}**

### 📈 Metrics:
- **Polarity:** {polarity_color} {result['polarity']} 
- **Subjectivity:** 🎯 {result['subjectivity']}
- **Confidence:** {result.get('confidence', 'N/A').title()}

### 📝 Statistics:
- **Words:** {result.get('word_count', 'N/A')}
- **Characters:** {result.get('character_count', 'N/A')}

### 💡 Interpretation:
{result.get('interpretation', 'No interpretation available')}

---
*🔗 This analysis is available via MCP protocol for AI assistants*
"""

# Gradio interface setup
with gr.Blocks(title="🎯 MCP Sentiment Analyzer") as demo:
    gr.HTML("""
    <h1 style="text-align: center; color: #667eea;">
        🎯 MCP-Enabled Sentiment Analyzer
    </h1>
    <p style="text-align: center; color: #666;">
        Advanced sentiment analysis with Model Context Protocol support
    </p>
    """)
    
    with gr.Tab("🔍 Single Analysis"):
        text_input = gr.Textbox(
            placeholder="Enter text for sentiment analysis...",
            lines=5,
            label="Text to Analyze"
        )
        analyze_btn = gr.Button("🔍 Analyze", variant="primary")
        output = gr.Markdown()
        
        analyze_btn.click(
            fn=lambda x: format_results(sentiment_analysis(x)),
            inputs=text_input,
            outputs=output
        )
    
    with gr.Tab("📊 Batch Analysis"):
        batch_input = gr.Textbox(
            placeholder="Enter multiple texts, one per line...",
            lines=8,
            label="Multiple Texts"
        )
        batch_btn = gr.Button("📊 Batch Analyze", variant="primary")
        batch_output = gr.JSON(label="Batch Results")
        
        def batch_analyze_wrapper(texts_str: str):
            if not texts_str.strip():
                return {"error": "Please enter some texts"}
            
            texts = [line.strip() for line in texts_str.split('\n') if line.strip()]
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(mcp_server.batch_analyze(texts))
            finally:
                loop.close()
        
        batch_btn.click(
            fn=batch_analyze_wrapper,
            inputs=batch_input,
            outputs=batch_output
        )
    
    with gr.Tab("📈 Summary Stats"):
        summary_input = gr.Textbox(
            placeholder="Enter texts for summary statistics...",
            lines=6,
            label="Texts for Summary"
        )
        summary_btn = gr.Button("📈 Get Summary", variant="primary")
        summary_output = gr.JSON(label="Summary Statistics")
        
        def summary_wrapper(texts_str: str):
            if not texts_str.strip():
                return {"error": "Please enter some texts"}
            texts = [line.strip() for line in texts_str.split('\n') if line.strip()]
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(mcp_server.sentiment_summary(texts))
            finally:
                loop.close()
        
        summary_btn.click(
            fn=summary_wrapper,
            inputs=summary_input,
            outputs=summary_output
        )

if __name__ == "__main__":
    print("🚀 Starting MCP-Enabled Sentiment Analyzer...")
    print("📡 MCP Server: Available for AI assistant integration")
    print("🔧 Available MCP tools:")
    print("  - analyze_sentiment: Single text analysis")
    print("  - batch_analyze: Multiple texts analysis") 
    print("  - sentiment_summary: Statistical summary")
    print("🌐 Web UI: http://localhost:7860")
    
    demo.launch(
        mcp_server=True,
        server_name="127.0.0.1",
        server_port=7860,
        inbrowser=True
    )