# 🎭 Playwright MCP Server with AI Agent

A comprehensive browser automation solution combining **Playwright** with **Model Context Protocol (MCP)** and an intelligent AI agent for natural language browser control.

## 🌟 Features

### 🤖 AI-Powered Browser Automation
- **Natural language commands** - Tell the AI what you want to do, it figures out how
- **Multiple LLM providers** - OpenAI GPT-4/5, Anthropic Claude, Google Gemini
- **Real-time feedback** - AI learns from each tool execution and adapts
- **Smart error recovery** - Automatic retries with intelligent modifications

### 🎭 Comprehensive Playwright Integration
- **Multi-browser support** - Chromium, Firefox, WebKit, Chrome, Microsoft Edge
- **49+ automation tools** - Navigation, interaction, extraction, debugging, and more
- **Advanced element handling** - Smart selectors, waits, fallback strategies
- **Network monitoring** - Request/response interception and analysis

### 🔌 Dual Transport Architecture
1. **🏠 Local Mode** - Direct tool calls (faster)
2. **📡 MCP Mode** - JSON-RPC over stdio (protocol compliant)

### 🛠️ Execution Modes
- **🚀 Batch Mode** - Execute all tools at once
- **🔄 Real-Time Feedback** - LLM feedback after each tool execution

## 🚀 Quick Start

### Prerequisites

#### System Requirements
- **Python 3.8+** (Python 3.10+ recommended)
- **Node.js** (for Playwright browser installation)
- **Git** (for cloning the repository)

#### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/ksmuvva/PLAYWRIGHT_MCP-WITH-AGENT.git
   cd PLAYWRIGHT_MCP-WITH-AGENT
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**
   ```bash
   playwright install
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env  # If .env.example exists
   # Edit .env file with your API keys
   ```

### Basic Usage

#### Interactive Mode
```bash
python Ai_agent_enhanced.py
```

#### Command Line Mode
```bash
# OpenAI + Chrome + MCP transport
python Ai_agent_enhanced.py --llm openai --browser chrome --transport mcp

# Anthropic + Firefox + Local transport
python Ai_agent_enhanced.py --llm anthropic --browser firefox --transport local
```

### Example Tasks

```bash
# E-commerce automation
"Go to https://www.saucedemo.com, log in with standard_user/secret_sauce, add 2 items to cart, and tell me the total price"

# Web scraping
"Navigate to https://example.com, extract all the headlines, and save them to a file"

# Form automation
"Fill out the contact form with my details and submit it"

# Testing workflows
"Test the login functionality with invalid credentials and verify error messages"
```

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Agent      │    │   MCP Server    │    │   Playwright    │
│                 │    │                 │    │                 │
│ • LLM Providers │◄──►│ • JSON-RPC      │◄──►│ • Multi-browser │
│ • Task Planning │    │ • Tool Registry │    │ • 49+ Tools     │
│ • Error Recovery│    │ • stdio Protocol│    │ • Smart Waits   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Tool Categories

- **🧭 Navigation** - URL navigation, page management, history
- **🎯 Element Location** - Smart selectors, XPath, text-based finding
- **🖱️ Element Interaction** - Click, fill, select, keyboard input
- **📄 Content Extraction** - Text, HTML, screenshots, PDFs
- **🌐 Network Monitoring** - Request interception, response analysis
- **🐛 Debug Tools** - Console logs, page state, element inspection
- **⚡ Advanced Browser** - Multiple tabs, contexts, mobile emulation
- **🤖 Code Generation** - Dynamic script generation from descriptions

## 🔧 Configuration

### Environment Variables (.env)
```bash
# LLM API Keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GEMINI_API_KEY=your_gemini_key

# Model Configuration
OPENAI_MODEL=gpt-4o-2024-08-06
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
GEMINI_MODEL=gemini-1.5-pro-002

# Browser Settings
DEFAULT_BROWSER=chromium
HEADLESS=false
```

### Supported Browsers
- **Chromium** - Default Playwright engine
- **Firefox** - Mozilla Firefox engine
- **WebKit** - Safari/WebKit engine  
- **Chrome** - Google Chrome (if installed)
- **Microsoft Edge** - Edge browser (if installed)

### Supported LLM Providers
- **OpenAI** - GPT-4, GPT-4 Turbo, GPT-5 (when available)
- **Anthropic** - Claude 3.5 Sonnet, Claude 3.5 Haiku
- **Google** - Gemini 1.5 Pro, Gemini 1.5 Flash

## 🎯 Use Cases

### 🛒 E-commerce Testing
```python
# Automated checkout flow testing
"Navigate to the online store, add items to cart, proceed through checkout, and verify the total matches expected prices"
```

### 📊 Data Extraction
```python
# Scrape dynamic content
"Go to the news website, wait for articles to load, extract all headlines and summaries, then save to CSV"
```

### 🧪 QA Automation
```python
# Form validation testing
"Test the registration form with various invalid inputs and document all error messages"
```

### 🔍 Competitive Analysis
```python
# Price monitoring
"Check competitor pricing on their product pages and create a comparison report"
```

## 🛠️ Development

### Project Structure
```
playwright_mcpserver/
├── Ai_agent_enhanced.py      # Main AI agent
├── mcp_client.py             # MCP JSON-RPC client
├── playwright_server.py      # MCP server implementation
├── Tools/                    # Playwright tool modules
│   ├── AdvancedBrowser/      # Multi-tab, context management
│   ├── BrowserControl/       # Navigation, page control
│   ├── CodeGeneration/       # Dynamic script generation
│   ├── ContentExtraction/    # Text, HTML, screenshot tools
│   ├── Debug/                # Debugging and inspection
│   ├── ElementInteraction/   # Click, fill, select tools
│   ├── ElementLocation/      # Element finding strategies
│   └── Network/              # Request/response monitoring
├── requirements.txt          # Python dependencies
├── TOOL_REFERENCE.md         # Tool usage reference
└── tests/                    # Test scripts
```

### Adding Custom Tools

1. Create tool class inheriting from `PlaywrightBase`
2. Implement async methods with proper typing
3. Add to server tool registry
4. Update documentation

Example:
```python
class CustomTools(PlaywrightBase):
    async def my_custom_tool(self, param: str) -> Dict[str, Any]:
        """Custom automation tool."""
        # Implementation here
        return {"status": "success", "result": "data"}
```

### Testing

```bash
# Test MCP stdio transport
python test_mcp_stdio.py

# Test direct tool calls
python test_mcp_direct.py

# Manual SauceDemo workflow test
python test_saucedemo_manual.py
```

## 📚 API Reference

### Core Tools

#### Navigation
- `playwright_navigate(url)` - Navigate to URL
- `playwright_go_back()` - Go back in history
- `playwright_go_forward()` - Go forward in history
- `playwright_reload()` - Reload current page

#### Element Interaction
- `playwright_click(selector)` - Click element
- `playwright_fill(selector, text)` - Fill form field ⚠️ Use `text`, not `value`
- `playwright_press_key(key)` - Press keyboard key
- `playwright_select_option(selector, value)` - Select dropdown option

#### Content Extraction
- `playwright_get_visible_text(selector)` - Extract visible text ⚠️ Correct name
- `playwright_get_visible_html(selector)` - Extract HTML content
- `playwright_screenshot(filename)` - Take screenshot
- `playwright_save_as_pdf(filename)` - Save page as PDF

#### Element Location
- `playwright_wait_for_element(selector, state)` - Wait for element
- `playwright_check_element(selector, property)` - Check element property
- `playwright_find_elements(selector)` - Find multiple elements

### Common Patterns

#### Login Flow
```python
# Navigate to login page
await playwright_navigate("https://example.com/login")

# Fill credentials (use 'text' parameter!)
await playwright_fill("#username", text="user@example.com")
await playwright_fill("#password", text="password123")

# Submit form
await playwright_click("button[type='submit']")

# Wait for redirect
await playwright_wait_for_element(".dashboard", state="visible")
```

#### Data Extraction
```python
# Navigate and wait for content
await playwright_navigate("https://example.com/data")
await playwright_wait_for_element(".content", state="visible")

# Extract text content
result = await playwright_get_visible_text(".data-container")
```

## 🔍 Troubleshooting

### Common Issues

#### "Tool 'playwright_get_text' not found"
- ✅ **Solution**: Use `playwright_get_visible_text` instead

#### "Unexpected keyword argument 'value'"
- ✅ **Solution**: Use `text` parameter in `playwright_fill`, not `value`

#### "Two browsers opening"
- ✅ **Solution**: Fixed in latest version - agent no longer initializes local browser in MCP mode

#### "Browser validation failed"
- ✅ **Solution**: Use MCP mode for better browser state management

### Debug Mode
Enable detailed logging:
```bash
export PLAYWRIGHT_DEBUG=1
python Ai_agent_enhanced.py --llm openai --browser chromium --transport mcp
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Include docstrings for public methods
- Add tests for new functionality
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Playwright** team for the excellent browser automation framework
- **Model Context Protocol (MCP)** for standardized tool communication
- **OpenAI**, **Anthropic**, and **Google** for powerful LLM APIs
- Open source community for inspiration and contributions

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/ksmuvva/PLAYWRIGHT_MCP-WITH-AGENT/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/ksmuvva/PLAYWRIGHT_MCP-WITH-AGENT/discussions)
- 📧 **Email**: For direct support, please create an issue on GitHub

---

## 🎯 Project Status

### ✅ Completed Features
- ✅ Full MCP JSON-RPC implementation
- ✅ Multi-browser support (Chromium, Firefox, WebKit, Chrome, Edge)
- ✅ Multi-LLM provider support (OpenAI, Anthropic, Gemini)
- ✅ 49+ Playwright automation tools
- ✅ Real-time feedback system
- ✅ Smart error recovery and retries
- ✅ Dual transport architecture (Local + MCP)
- ✅ Interactive CLI with configuration selection
- ✅ Comprehensive logging and debugging

### 🚀 Recent Fixes
- ✅ Fixed browser type selection (Firefox now actually opens Firefox)
- ✅ Fixed dual browser opening issue in MCP mode
- ✅ Corrected tool parameter names (`text` vs `value`)
- ✅ Enhanced OpenAI token limit handling
- ✅ Improved error messaging and fallbacks

### 🔜 Planned Enhancements
- 🔮 Visual element recognition using AI
- 🔮 Advanced workflow recording and playback
- 🔮 Integration with popular testing frameworks
- 🔮 Performance monitoring and optimization
- 🔮 Multi-page parallel execution

---

**🎭 Happy Automating!** 🤖✨
