***Hands-on with MCP servers:***

Project setup:
<notes>

<critical>

Below are notes from a video course about working with the Claude language model.

Use these notes as a resource to answer the user's question.

Write your answer as a standalone response - do not refer directly to these notes unless specifically requested by the user.

</critical>

<note title="Introducing MCP">

MCP = Model Context Protocol, communication layer providing Claude with context and tools without requiring developers to write tedious code.



Core Architecture: MCP client connects to MCP server. MCP server contains tools, resources, and prompts as internal components.



Problem Solved: Traditional approach requires developers to manually author tool schemas and functions for each service integration (like GitHub API tools). This creates maintenance burden for complex services with many features.



MCP Solution: Shifts tool definition and execution from developer's server to dedicated MCP server. MCP server = interface to outside service, wrapping functionality into pre-built tools.



Key Benefits: Eliminates need for developers to write/maintain tool schemas and function implementations. Someone else authors the tools, packages them in MCP server.



Common Questions:

\- Who authors MCP servers? Anyone, but often service providers create official implementations

\- Difference from direct API calls? Saves developer time by providing pre-built tool schemas/functions instead of manual authoring

\- Relationship to tool use? MCP and tool use are complementary, not identical. MCP focuses on who does the work of creating tools



Core Value: Reduces developer burden by outsourcing tool creation to MCP server implementations rather than requiring custom tool development for each service integration.

</note>



<note title="MCP Clients">

MCP Client = communication interface between your server and MCP server, provides access to server's tools.



Transport agnostic = client/server can communicate via multiple protocols (stdin/stdout, HTTP, WebSockets, etc). Common setup: both on same machine using stdin/stdout.



Communication = message exchange defined by MCP spec. Key message types:

\- list tools request/result = client asks server for available tools, server responds with tool list

\- call tool request/result = client asks server to run tool with arguments, server returns execution result



Typical flow: User query → Server asks MCP client for tools → MCP client sends list tools request to MCP server → Server gets tool list → Server sends query + tools to Claude → Claude requests tool execution → Server asks MCP client to run tool → MCP client sends call tool request to MCP server → MCP server executes tool (e.g., GitHub API call) → Results flow back through chain → Claude formulates final response → User gets answer.



MCP client acts as intermediary - doesn't execute tools itself, just facilitates communication between your server and MCP server that actually runs the tools.

</note>



<note title="Project Setup">

MCP Learning Project = CLI-based chatbot implementing both client and server components for educational purposes.



Project Structure = Custom MCP client connects to custom MCP server, both built in same project.



Document System = Fake documents stored in memory only, no persistence.



Server Tools = Two tools implemented: read document contents, update document contents.



Real-world Context = Normally projects implement either client OR server, not both. This project does both for learning.



Setup Requirements = Download CLI\_project.zip, extract, configure .env with API key, install dependencies.



Running Project = "uv run main.py" (with UV) or "python main.py" (without UV).



Verification = Chat prompt appears, responds to basic queries like "what's one plus one".

</note>



<note title="Defining Tools with MCP">

MCP server implementation = Python SDK simplifies tool creation vs manual JSON schemas



Tool definition syntax = @mcp.tool decorator + function with typed parameters + Field descriptions



Document storage = in-memory dictionary with doc\_id keys and content values



Tool 1 - read\_doc\_contents = takes doc\_id string parameter, returns document content from docs dictionary, raises ValueError if doc not found



Tool 2 - edit\_document = takes doc\_id, old\_string, new\_string parameters, performs find/replace operation on document content, includes existence validation



MCP Python SDK benefits = auto-generates JSON schemas from decorated functions, single line server creation, eliminates manual schema writing



Parameter definition = use Field() with description for tool arguments, import from pydantic



Error handling = validate document existence before operations, raise ValueError for missing documents



Implementation pattern = decorator → function definition → parameter typing → validation → core logic

</note>



<note title="The Server Inspector">

MCP Inspector = in-browser debugger for testing MCP servers without connecting to actual applications



Access: Run \\`mcp dev \[server\_file.py]\\` in terminal with activated Python environment → opens server on port → visit provided localhost address



Interface: Left sidebar with Connect button → top navigation bar shows Resources/Prompts/Tools sections → Tools section lists available tools → click tool to open right panel for manual testing



Testing process: Select tool → input required parameters (like document ID) → click Run Tool → verify output/success message



Key features: Live development testing, tool invocation simulation, parameter input fields, success/failure feedback



Status: Inspector in active development - UI may change but core functionality remains similar



Usage pattern: Essential for MCP server development and debugging before production deployment

</note>



<note title="Implementing a Client">

MCP Client Implementation:



MCP Client = wrapper class around client session for connecting to MCP server with resource cleanup management



Client Session = actual connection to MCP server from MCP Python SDK, requires cleanup when closing



Resource Cleanup = necessary process when shutting down, handled by connect/cleanup/async enter/async exit functions



Client Purpose = exposes MCP server functionality to rest of codebase, provides interface between application code and server



Key Functions:

\- list\_tools() = await self.session.list\_tools(), return result.tools

\- call\_tool() = await self.session.call\_tool(tool\_name, tool\_input)



Implementation Flow:

1\. Application requests tool list for Claude

2\. Client calls list\_tools() to get server's available tools

3\. Claude selects tool and provides parameters

4\. Client calls call\_tool() to execute on server

5\. Results returned to Claude



Testing = run MCP client.py directly with testing harness to verify connection and tool listing



Integration = once implemented, can run CLI to have Claude use tools (e.g., "what is contents of report.pdf document")



Common Practice = wrap client session in larger class rather than using directly for better resource management

</note>



<note title="Defining Resources">

Resources = MCP server feature that exposes data to clients for read operations



Resource types:

\- Direct/Static = static URI (e.g., docs://documents)

\- Templated = parameterized URI with wildcards (e.g., documents/{doc\_id})



Resource flow:

1\. Client sends read resource request with URI

2\. MCP server matches URI to resource function

3\. Server executes function, returns result

4\. Client receives data via read resource result message



Implementation:

\- Use @mcp.resource decorator

\- Define URI (route-like address)

\- Set MIME type (application/json, text/plain, etc.)

\- Templated resources: URI parameters become function keyword arguments

\- Python MCP SDK auto-serializes return values to strings



Common pattern = One resource per distinct read operation (list items vs fetch single item)



MIME types = hints to client about returned data format for proper deserialization

</note>



<note title="Accessing Resources">

MCP Resource Access = method for clients to retrieve data from server resources



Client Implementation:

\- read\_resource function = takes URI parameter, requests resource from MCP server

\- Uses await self.session.read\_resource(AnyUrl(uri)) for server communication

\- Accesses result.contents\[0] = first resource from returned contents list



Response Parsing:

\- Checks resource.mime\_type property to determine data format

\- If mime\_type == "application/json": returns json.loads(resource.text)

\- Otherwise: returns resource.text as plain text



Resource Integration:

\- MCP client functions called by other application components

\- Enables document selection via CLI interface with arrow keys + space

\- Selected resource contents automatically included in LLM prompts

\- Eliminates need for tools to read document contents during chat



Key Dependencies: json module, pydantic.AnyUrl for type handling

</note>



<note title="Defining Prompts">

Prompts = pre-written, tested instructions that MCP servers expose to clients for specialized tasks



MCP Prompts Feature:

\- Servers define high-quality prompts tailored to their domain

\- Clients can access these prompts via slash commands (e.g., /format)

\- Alternative to users writing their own prompts manually



Implementation Pattern:

\- Use @prompt decorator with name and description

\- Function receives arguments (e.g., document ID)

\- Returns list of messages (user/assistant format)

\- Messages sent directly to Claude



Key Benefit: Server authors create optimized, tested prompts rather than leaving prompt quality to end users



Example Structure:

\\`\\`\\`

@prompt(name="format", description="rewrites document in markdown")

def format\_document(doc\_id: str) -> list\[messages]:

&#x20;   return \[base.user\_message(prompt\_text)]

\\`\\`\\`



Workflow: User types /format → selects document → server returns specialized prompt → client sends to Claude → Claude uses tools to read/reformat/save document



Purpose = encapsulate domain expertise in prompt engineering within specialized MCP servers

</note>



<note title="Prompts in the Client">

MCP Client Prompt Implementation:



List prompts function = await self.session.list\_prompts(), return result.props



Get prompt function = await self.session.get\_prompt(prompt\_name, arguments), return result.messages



Prompt workflow = Client requests prompt by name → passes arguments as keyword parameters → MCP server interpolates arguments into prompt template → returns formatted messages for AI model



Arguments flow = Client arguments → prompt function keyword arguments → interpolated into prompt text (e.g., document\_id parameter gets inserted into prompt template)



Return format = Messages array that forms conversation input for AI model



CLI usage = /format command → select document → prompt with document ID sent to Claude → Claude uses tools to fetch document → returns formatted result



Key concept = Prompts are server-defined templates that clients can invoke with parameters, enabling reusable AI instructions with dynamic content insertion.

</note>



<note title="MCP Review">

MCP Server Primitives = 3 types: tools, resources, prompts



Tools = model-controlled primitives where Claude decides when to execute them. Used to add capabilities to Claude (e.g., JavaScript execution for calculations). Serve the model.



Resources = app-controlled primitives where application code decides when to fetch data. Used to get data into apps for UI display or prompt augmentation (e.g., autocomplete options, document listings from Google Drive). Serve the app.



Prompts = user-controlled primitives triggered by user actions like button clicks or slash commands. Used for predefined workflows (e.g., chat starter buttons in Claude interface). Serve users.



Control patterns determine purpose: Need Claude capabilities → implement tools. Need app data → use resources. Need user workflows → create prompts.



Real examples: Claude's chat starter buttons use prompts, Google Drive document selection uses resources, code execution uses tools.

</note>

</notes>

Defining Tools with MCP:
Building an MCP server becomes much simpler when you use the official Python SDK. Instead of writing complex JSON schemas by hand, you can define tools with decorators and let the SDK handle the heavy lifting.







In this example, we're creating a document management server with two core tools: one to read documents and another to update them. All documents exist in memory as a simple dictionary where keys are document IDs and values are the content.



Setting Up the MCP Server

The Python MCP SDK makes server creation straightforward. You can initialize a server with just one line:



from mcp.server.fastmcp import FastMCP



mcp = FastMCP("DocumentMCP", log\_level="ERROR")

Your documents can be stored in a simple dictionary structure:



docs = {

&#x20;   "deposition.md": "This deposition covers the testimony of Angela Smith, P.E.",

&#x20;   "report.pdf": "The report details the state of a 20m condenser tower.",

&#x20;   "financials.docx": "These financials outline the project's budget and expenditures",

&#x20;   "outlook.pdf": "This document presents the projected future performance of the system",

&#x20;   "plan.md": "The plan outlines the steps for the project's implementation.",

&#x20;   "spec.txt": "These specifications define the technical requirements for the equipment"

}

Tool Definition with Decorators

The SDK uses decorators to define tools. Instead of writing JSON schemas manually, you can use Python type hints and field descriptions. The SDK automatically generates the proper schema that Claude can understand.



Creating a Document Reader Tool

The first tool reads document contents by ID. Here's the complete implementation:



@mcp.tool(

&#x20;   name="read\_doc\_contents",

&#x20;   description="Read the contents of a document and return it as a string."

)

def read\_document(

&#x20;   doc\_id: str = Field(description="Id of the document to read")

):

&#x20;   if doc\_id not in docs:

&#x20;       raise ValueError(f"Doc with id {doc\_id} not found")

&#x20;   

&#x20;   return docs\[doc\_id]

The decorator specifies the tool name and description, while the function parameters define the required arguments. The Field class from Pydantic provides argument descriptions that help Claude understand what each parameter expects.



Building a Document Editor Tool

The second tool performs simple find-and-replace operations on documents:



@mcp.tool(

&#x20;   name="edit\_document",

&#x20;   description="Edit a document by replacing a string in the documents content with a new string."

)

def edit\_document(

&#x20;   doc\_id: str = Field(description="Id of the document that will be edited"),

&#x20;   old\_str: str = Field(description="The text to replace. Must match exactly, including whitespace."),

&#x20;   new\_str: str = Field(description="The new text to insert in place of the old text.")

):

&#x20;   if doc\_id not in docs:

&#x20;       raise ValueError(f"Doc with id {doc\_id} not found")

&#x20;   

&#x20;   docs\[doc\_id] = docs\[doc\_id].replace(old\_str, new\_str)

This tool takes three parameters: the document ID, the text to find, and the replacement text. The implementation includes error handling for missing documents and performs a straightforward string replacement.



Key Benefits of the SDK Approach

No manual JSON schema writing required

Type hints provide automatic validation

Clear parameter descriptions help Claude understand tool usage

Error handling integrates naturally with Python exceptions

Tool registration happens automatically through decorators

The MCP Python SDK transforms tool creation from a complex schema-writing exercise into simple Python function definitions. This approach makes it much easier to build and maintain MCP servers while ensuring Claude receives properly formatted tool specifications.

The Server Inspector:
When building MCP servers, you need a way to test your functionality without connecting to a full application. The Python MCP SDK includes a built-in browser-based inspector that lets you debug and test your server in real-time.



Starting the Inspector

First, make sure your Python environment is activated (check your project's README for the exact command). Then run the inspector with:



mcp dev mcp\_server.py

This starts a development server and gives you a local URL, typically something like http://127.0.0.1:6274. Open this URL in your browser to access the MCP Inspector.



Using the Inspector Interface

The inspector interface is actively being developed, so it may look different when you use it. However, the core functionality remains consistent. Look for these key elements:



A Connect button to start your MCP server

Navigation tabs for Resources, Tools, Prompts, and other features

A tools listing and testing panel

Click the Connect button first to initialize your server. You'll see the connection status change from "Disconnected" to "Connected".



Testing Your Tools

Navigate to the Tools section and click "List Tools" to see all available tools from your server. When you select a tool, the right panel shows its details and input fields.







For example, to test a document reading tool:



Select the read\_doc\_contents tool

Enter a document ID (like "deposition.md")

Click "Run Tool"

Check the results for success and expected output

The inspector shows both the success status and the actual returned data, making it easy to verify your tool works correctly.



Testing Tool Interactions

You can test multiple tools in sequence to verify complex workflows. For instance, after using an edit tool to modify a document, immediately test the read tool to confirm the changes were applied correctly.



The inspector maintains your server state between tool calls, so edits persist and you can verify the complete functionality of your MCP server.



Development Workflow

The MCP Inspector becomes an essential part of your development process. Instead of writing separate test scripts or connecting to full applications, you can:



Quickly iterate on tool implementations

Test edge cases and error conditions

Verify tool interactions and state management

Debug issues in real-time

This immediate feedback loop makes MCP server development much more efficient and helps catch issues early in the development process.



