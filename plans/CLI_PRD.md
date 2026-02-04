# Grok CLI UI Product Requirements Document

## **Overview**
Grok CLI is a conversational AI assistant that runs in the terminal. The interface provides a chat-like experience with real-time streaming responses, tool execution confirmations, and interactive features. The UI is designed to be fully functional within a text-based terminal environment, utilizing ANSI color codes for visual elements and structured layouts for clarity.

## **Core UI Architecture**

### **Layout Principles**
- **Grid-Based**: The interface uses a vertical stack layout divided into sections with horizontal separators.
- **Colors**: ANSI escape codes for text coloring and styling, with semantic meanings for different UI elements.
- **Input Handling**: Responsive to keyboard input, supporting single-line, multi-line, and special command modes.
- **Responsiveness**: Adapts to terminal width, with minimum recommended width of 80 characters.

### **Screen Layout Structure**
```
┌─────────────────────────────────────────────────┐
│                                                 │
│  GROK (ASCII Art Logo)                          │
│                                                 │
│  Welcome Message & Instructions                 │
│  (shown only on first launch)                   │
│                                                 │
│  ────────────────────────────────────────────── │
│                                                 │
│  Chat History                                   │
│  (scrollable conversation)                      │
│                                                 │
│  ────────────────────────────────────────────── │
│                                                 │
│  [Loading Spinner] (when processing)            │
│                                                 │
│  Input Box                                      │
│  └─────────────────────────────────────────────┘│
│                                                 │
│  Status Bar                                     │
│  [auto-edit status] [model] [MCP status]        │
│                                                 │
│  [Command Suggestions] (when typing /command)   │
│  [Model Selection] (when switching models)      │
│                                                 │
└─────────────────────────────────────────────────┘
```

## **Detailed Component Specifications**

### **1. Application Header**
- **Logo**: ASCII art "GROK" displayed in a gradient from magenta to cyan.
- **Position**: Top of screen, centered or left-aligned depending on terminal width.
- **Padding**: 2 spaces from left edge.

### **2. Welcome Message (First Launch Only)**
```
🤖 Welcome to Grok CLI Conversational Assistant!

Getting Started:
1. Ask questions, edit files, or run commands.
2. Be specific for the best results.
3. Create GROK.md files to customize your interactions with Grok.
4. Press Shift+Tab to toggle auto-edit mode.
5. /help for more information.
```
- **Colors**: Gray text.
- **Display**: Only shown when chat history is empty.

### **3. Help Text (Persistent)**
```
Type your request in natural language. Ctrl+C to clear, 'exit' to quit.
```
- **Color**: Gray.
- **Position**: Above chat history.

### **4. Chat History Component**

#### **User Messages**
```
> Your message here
```
- **Prefix**: `>` in gray.
- **Color**: Gray text.
- **Layout**: Single line, with word wrapping if necessary.

#### **Assistant Messages**
```
⏺ Response content here (rendered text)
```
- **Prefix**: `⏺` in white.
- **Content**: White text, with basic formatting for readability.
- **Streaming**: Displays a `█` cursor in cyan during streaming.
- **Spacing**: 1 line margin above each message.

#### **Tool Execution Messages**
```
Tool Action Format:
[Icon] ActionName: context details

Examples:
📖 Read: filename.txt (lines 1-50)
✏️ Update: filename.txt (Replacing 150 → 200 chars)
📝 Create: filename.txt (Creating (1024 chars))
💻 Bash: Running: git status --porcelain
🔍 Search: Searching for "import react"
📋 Created Todo: Added 3 new tasks
🔄 Updated Todo: Marked task as completed
```
- **Icons**: Unicode symbols for different tool types.
- **Colors**:
  - Icon: White
  - Action: White
  - Context: Gray
- **Tool Name Mapping**:
  - `view_file` → "Read"
  - `str_replace_editor` → "Update"
  - `create_file` → "Create"
  - `bash` → "Bash"
  - `search` → "Search"
  - `create_todo_list` → "Created Todo"
  - `update_todo_list` → "Updated Todo"

#### **MCP Tools**
```
ServerName(Tool Name): context
```
- **Format**: `ServerName(tool_name_with_spaces)`
- **Example**: `GitHub(get pull request)`

### **5. Loading Spinner Component**
```
◐ Thinking... (2.3s · ↑ 1.2K tokens · esc to interrupt)
```
- **Spinner Frames**: `/`, `-`, `\`, `|` (rotates every 500ms).
- **Loading Texts**: Random from 16 options including "Thinking...", "Computing...", "Analyzing...", etc.
- **Text Change**: Every 4 seconds when active.
- **Colors**:
  - Spinner: Cyan
  - Text: Cyan
  - Stats: Gray
- **Stats Format**: `(time)s · ↑ token_count tokens · esc to interrupt`
- **Token Formatting**:
  - < 1000: "500"
  - 1000-999999: "1.2K", "45.8K"
  - ≥1000000: "1.2M"

### **6. Input Component**

#### **Single Line Mode**
```
┌─────────────────────────────────────┐
│❯ Ask me anything...                 │
└─────────────────────────────────────┘
```
- **Border**: Rounded corners.
- **Border Color**: Blue (idle), Yellow (processing/streaming).
- **Prompt**: `❯` in cyan.
- **Placeholder**: "Ask me anything..." in dim gray.
- **Cursor**: Highlighted with white background, black text.

#### **Multiline Mode**
```
┌─────────────────────────────────────┐
│❯ First line                         │
││  Second line                        │
│↳ Third line (with cursor)           │
└─────────────────────────────────────┘
```
- **Continuation Prompt**: `│` for continuation lines, `↳` for current line.
- **Border**: Same as single line.
- **Cursor**: Same highlight behavior.

### **7. Status Bar**
```
▶ auto-edit: on  (shift + tab)    ≋ grok-4-fast-reasoning    [MCP: connected]
```
- **Components**:
  - **Auto-edit Status**: `▶` (on) or `⏸` (off) in cyan + "auto-edit: on/off"
  - **Model**: `≋ model_name` in yellow
  - **MCP Status**: `[MCP: status]` (color varies by status)
- **Layout**: Horizontal row with spaces between elements.
- **Position**: Below input box.

### **8. Command Suggestions**
```
  /help      Show available commands
  /clear     Clear chat history
> /exit      Exit the application
   ↑↓ navigate • Enter/Tab select • Esc cancel
```
- **Trigger**: When input starts with `/`.
- **Filtering**: Commands starting with input text (case-insensitive).
- **Max Items**: 8 suggestions.
- **Colors**:
  - Selected: Black text on cyan background
  - Unselected: White text
  - Description: Gray
- **Navigation**: ↑↓ arrows or Tab to navigate, Enter/Tab to select, Esc to cancel.
- **Help Text**: "↑↓ navigate • Enter/Tab select • Esc cancel" in dim gray.

### **9. Model Selection**
```
Available Models:
  grok-4-1-fast-reasoning
> grok-4-1-fast-non-reasoning
  grok-4-fast-reasoning
   ↑↓ navigate • Enter select • Esc cancel
```
- **Trigger**: When user types `/model` or presses specific key combo.
- **Colors**: Same as command suggestions.
- **Navigation**: Same as command suggestions.
- **Current Model Indicator**: Shows current model name in status bar.

### **10. Confirmation Dialog**
```
Operation: Update file
File: example.txt
Content: (shows diff or content preview)

Yes
> Yes, and don't ask again this session
  No
  No, with feedback

↑↓ navigate • Enter select • Esc cancel
```
- **Options**:
  1. Yes
  2. Yes, and don't ask again this session
  3. No
  4. No, with feedback (opens feedback input)
- **Colors**:
  - Selected: Black on cyan
  - Unselected: White
- **Navigation**: ↑↓ or Tab, Enter to select.
- **Feedback Mode**: When "No, with feedback" selected, shows input box for feedback.

#### **Feedback Input Mode**
```
Type your feedback and press Enter, or press Escape to go back.

┌─────────────────────────────────────┐
│❯ Your feedback here                 │
└─────────────────────────────────────┘
```
- **Prompt**: Yellow border.
- **Input**: Same as main input component.

### **11. Diff Renderer**
For file changes, shows diffs:
```
example.py
────────────────────────────────────────────────────────────────────────────────
  1 | def hello():
- 2 |     print("Hello World")
+ 2 |     print("Hello Grok")
  3 |
```
- **Header**: Filename in white.
- **Separator**: Gray line.
- **Colors**:
  - Added lines: Green `+`
  - Removed lines: Red `-`
  - Context: Gray
  - Line numbers: Gray

### **Color Palette**
- **White**: Primary text
- **Gray**: Secondary text, instructions
- **Dim Gray**: Placeholder text, help text
- **Cyan**: Prompts, spinner, auto-edit status, streaming cursor
- **Yellow**: Model name, processing borders
- **Blue**: Idle input borders
- **Green**: Diff additions
- **Red**: Diff deletions
- **Magenta**: Logo gradient start
- **Black**: Selected text background

### **Interaction Patterns**

#### **Keyboard Shortcuts**
- **Enter**: Send message / confirm selection
- **Shift+Tab**: Toggle auto-edit mode
- **Ctrl+C**: Clear input (if not processing)
- **Escape**: Cancel current operation, close menus
- **Tab**: Navigate menus forward
- **Shift+Tab**: Navigate menus backward
- **↑↓ Arrows**: Navigate menus

#### **Input Modes**
- **Single Line**: Default for short messages
- **Multiline**: Automatically activated for multi-line input (when Enter pressed mid-line)
- **Command Mode**: When input starts with `/`, shows command suggestions
- **Processing**: Input disabled, shows spinner
- **Confirmation**: All input redirected to confirmation dialog

#### **Scrolling**
- **Chat History**: Automatically scrolls to bottom on new messages
- **Terminal Scrolling**: Uses terminal's native scrolling for overflow

### **State Management**
- **Session Flags**: Control auto-approval for file/bash operations
- **Confirmation State**: Tracks pending confirmations
- **Input State**: Current text, cursor position, multiline mode
- **UI State**: Loading, streaming, menu visibility

### **Responsive Design**
- **Terminal Width**: Adapts to terminal width (minimum 80 chars recommended)
- **Word Wrapping**: Text wraps within component boundaries
- **Truncation**: Long commands/paths truncated with "..." when displayed

### **Error Handling**
- **Network Errors**: Show error messages in chat history
- **Invalid Input**: Clear input and show error state
- **Tool Failures**: Display error messages from tool execution

### **Performance Considerations**
- **Re-rendering**: Minimize updates of chat history
- **Memory**: Limit chat history size
- **Animation**: Smooth spinner rotation, text changes every 4s
- **Input Responsiveness**: Real-time cursor updates, immediate key response

This PRD provides the complete specification for recreating the Grok CLI UI in a technology-agnostic manner. The interface prioritizes clarity, responsiveness, and a conversational feel while maintaining the technical precision needed for development tools.