***Connecting with MCP clients:***

Implementing a client:
Now that we have our MCP server working, it's time to build the client side. The client is what allows our application code to communicate with the MCP server and access its functionality.



Understanding the Client Architecture

In most real-world projects, you'll either implement an MCP client or an MCP server - not both. We're building both in this project just so you can see how they work together.





The MCP client consists of two main components:



MCP Client - A custom class we create to make using the session easier

Client Session - The actual connection to the server (part of the MCP Python SDK)



The client session requires careful resource management - we need to properly clean up connections when we're done. That's why we wrap it in our own class that handles all the cleanup automatically.



How the Client Fits Into Our Application

Remember our application flow diagram? The client is what enables our code to interact with the MCP server at two key points:





Our CLI code uses the client to:



Get a list of available tools to send to Claude

Execute tools when Claude requests them

Implementing Core Client Functions

We need to implement two essential functions: list\_tools() and call\_tool().



List Tools Function

This function gets all available tools from the MCP server:



async def list\_tools(self) -> list\[types.Tool]:

&#x20;   result = await self.session().list\_tools()

&#x20;   return result.tools

It's straightforward - we access our session (the connection to the server), call the built-in list\_tools() method, and return the tools from the result.



Call Tool Function

This function executes a specific tool on the server:



async def call\_tool(

&#x20;   self, tool\_name: str, tool\_input: dict

) -> types.CallToolResult | None:

&#x20;   return await self.session().call\_tool(tool\_name, tool\_input)

We pass the tool name and input parameters (provided by Claude) to the server and return the result.



Testing the Client

The client file includes a simple test harness at the bottom. You can run it directly to verify everything works:



uv run mcp\_client.py

This will connect to your MCP server and print out the available tools. You should see output showing your tool definitions, including descriptions and input schemas.



Putting It All Together

Once the client functions are implemented, you can test the complete flow by running your main application:



uv run main.py

Try asking: "What is the contents of the report.pdf document?"



Here's what happens behind the scenes:



Your application uses the client to get available tools

These tools are sent to Claude along with your question

Claude decides to use the read\_doc\_contents tool

Your application uses the client to execute that tool

The result is returned to Claude, who then responds to you

The client acts as the bridge between your application logic and the MCP server's functionality, making it easy to integrate powerful tools into your AI workflows.

Defining Resources:
Resources in MCP servers allow you to expose data to clients, similar to GET request handlers in a typical HTTP server. They're perfect for scenarios where you need to fetch information rather than perform actions.



Understanding Resources Through an Example

Let's say you want to build a document mention feature where users can type @document\_name to reference files. This requires two operations:



Getting a list of all available documents (for autocomplete)

Fetching the contents of a specific document (when mentioned)





When a user mentions a document, your system automatically injects the document's contents into the prompt sent to Claude, eliminating the need for Claude to use tools to fetch the information.







How Resources Work

Resources follow a request-response pattern. When your client needs data, it sends a ReadResourceRequest with a URI to identify which resource it wants. The MCP server processes this request and returns the data in a ReadResourceResult.







The flow looks like this: your code requests a resource from the MCP client, which forwards the request to the MCP server. The server processes the URI, runs the appropriate function, and returns the result.







Types of Resources

There are two types of resources:



Direct Resources

Direct resources have static URIs that never change. They're perfect for operations that don't need parameters.



@mcp.resource(

&#x20;   "docs://documents",

&#x20;   mime\_type="application/json"

)

def list\_docs() -> list\[str]:

&#x20;   return list(docs.keys())

Templated Resources

Templated resources include parameters in their URIs. The Python SDK automatically parses these parameters and passes them as keyword arguments to your function.



@mcp.resource(

&#x20;   "docs://documents/{doc\_id}",

&#x20;   mime\_type="text/plain"

)

def fetch\_doc(doc\_id: str) -> str:

&#x20;   if doc\_id not in docs:

&#x20;       raise ValueError(f"Doc with id {doc\_id} not found")

&#x20;   return docs\[doc\_id]





Implementation Details

Resources can return any type of data - strings, JSON, binary data, etc. Use the mime\_type parameter to give clients a hint about what kind of data you're returning:



"application/json" for structured data

"text/plain" for plain text

"application/pdf" for binary files

The MCP Python SDK automatically serializes your return values. You don't need to manually convert objects to JSON strings - just return the data structure and let the SDK handle serialization.



Testing Your Resources

You can test resources using the MCP Inspector. Start your server with:



uv run mcp dev mcp\_server.py

Then connect to the inspector in your browser. You'll see two sections:



Resources - Lists your direct/static resources

Resource Templates - Lists your templated resources





Click on any resource to test it. For templated resources, you'll need to provide values for the parameters. The inspector shows you the exact response structure your client will receive, including the MIME type and serialized data.



Resources provide a clean way to expose read-only data from your MCP server, making it easy for clients to fetch information without the complexity of tool calls.

Accessing Resources:
Resources in MCP allow your server to expose information that can be directly included in prompts, rather than requiring tool calls to access data. This creates a more efficient way to provide context to AI models.





The diagram above shows how resources work: when a user types something like "What's in the @..." our code recognizes this as a resource request, sends a ReadResourceRequest to the MCP server, and gets back a ReadResourceResult with the actual content.



Implementing Resource Reading

To enable resource access in your MCP client, you need to implement a read\_resource function. First, add the necessary imports:



import json

from pydantic import AnyUrl

The core function makes a request to the MCP server and processes the response based on its MIME type:



async def read\_resource(self, uri: str) -> Any:

&#x20;   result = await self.session().read\_resource(AnyUrl(uri))

&#x20;   resource = result.contents\[0]

&#x20;   

&#x20;   if isinstance(resource, types.TextResourceContents):

&#x20;       if resource.mimeType == "application/json":

&#x20;           return json.loads(resource.text)

&#x20;   

&#x20;   return resource.text

Understanding the Response Structure

When you request a resource, the server returns a result with a contents list. We access the first element since we typically only need one resource at a time. The response includes:



The actual content (text or data)

A MIME type that tells us how to parse the content

Other metadata about the resource

Content Type Handling

The function checks the MIME type to determine how to process the content:



If it's application/json, parse the text as JSON and return the parsed object

Otherwise, return the raw text content

This approach handles both structured data (like JSON) and plain text documents seamlessly.



Testing Resource Access

Once implemented, you can test the resource functionality through your CLI application. When you type "@" followed by a resource name, the system will:



Show available resources in an autocomplete list

Let you select a resource using arrow keys and space

Include the resource content directly in your prompt

Send everything to the AI model without requiring additional tool calls

This creates a much smoother user experience compared to having the AI model make separate tool calls to access document contents. The resource content becomes part of the initial context, allowing for immediate responses about the data.


Defining Prompts:
Prompts in MCP servers let you define pre-built, high-quality instructions that clients can use instead of writing their own prompts from scratch. Think of them as carefully crafted templates that give better results than what users might come up with on their own.





Why Use Prompts?

Here's the key insight: users can already ask Claude to do most tasks directly. For example, a user could type "reformat the report.pdf in markdown" and get decent results. But they'll get much better results if you provide a thoroughly tested, specialized prompt that handles edge cases and follows best practices.



As the MCP server author, you can spend time crafting, testing, and evaluating prompts that work consistently across different scenarios. Users benefit from this expertise without having to become prompt engineering experts themselves.





Building a Format Command

Let's implement a practical example: a format command that converts documents to markdown. Users will type /format doc\_id and get back a professionally formatted markdown version of their document.



The workflow looks like this:



User types / to see available commands

They select format and specify a document ID

Claude uses your pre-built prompt to read and reformat the document

The result is clean markdown with proper headers, lists, and formatting

Defining Prompts

Prompts use a similar decorator pattern to tools and resources:



@mcp.prompt(

&#x20;   name="format",

&#x20;   description="Rewrites the contents of the document in Markdown format."

)

def format\_document(

&#x20;   doc\_id: str = Field(description="Id of the document to format")

) -> list\[base.Message]:

&#x20;   prompt = f"""

Your goal is to reformat a document to be written with markdown syntax.



The id of the document you need to reformat is:

<document\_id>

{doc\_id}

</document\_id>



Add in headers, bullet points, tables, etc as necessary. Feel free to add in structure.

Use the 'edit\_document' tool to edit the document. After the document has been reformatted...

"""

&#x20;   

&#x20;   return \[

&#x20;       base.UserMessage(prompt)

&#x20;   ]

The function returns a list of messages that get sent directly to Claude. You can include multiple user and assistant messages to create more complex conversation flows.



Testing Your Prompts

Use the MCP Inspector to test your prompts before deploying them:





The inspector shows you exactly what messages will be sent to Claude, including how variables get interpolated into your prompt template. This lets you verify the prompt looks correct before users start relying on it.



Key Benefits

Consistency - Users get reliable results every time

Expertise - You can encode domain knowledge into prompts

Reusability - Multiple client applications can use the same prompts

Maintenance - Update prompts in one place to improve all clients

Prompts work best when they're specialized for your MCP server's domain. A document management server might have prompts for formatting, summarizing, or analyzing documents. A data analysis server might have prompts for generating reports or visualizations.



The goal is to provide prompts that are so well-crafted and tested that users prefer them over writing their own instructions from scratch.

Prompts in the Client:
The final step in building our MCP client is implementing prompt functionality. This allows us to list all available prompts from the server and retrieve specific prompts with variables filled in.



Implementing List Prompts

The list\_prompts method is straightforward. It calls the session's list prompts function and returns the prompts:



async def list\_prompts(self) -> list\[types.Prompt]:

&#x20;   result = await self.session().list\_prompts()

&#x20;   return result.prompts

Getting Individual Prompts

The get\_prompt method is more interesting because it handles variable interpolation. When you request a prompt, you provide arguments that get passed to the prompt function as keyword arguments:



async def get\_prompt(self, prompt\_name, args: dict\[str, str]):

&#x20;   result = await self.session().get\_prompt(prompt\_name, args)

&#x20;   return result.messages

For example, if your server has a format\_document prompt that expects a doc\_id parameter, the arguments dictionary would contain {"doc\_id": "plan.md"}. This value gets interpolated into the prompt template.



Testing Prompts in Action

Once implemented, you can test prompts through the CLI. When you type a slash (/), available prompts appear as commands. Selecting a prompt like "format" will prompt you to choose from available documents.







After selecting a document, the system sends the complete prompt to Claude. The AI receives both the formatting instructions and the document ID, then uses available tools to fetch and process the content.



How Prompts Work





Prompts define a set of user and assistant messages that clients can use. They should be high-quality, well-tested, and relevant to your MCP server's purpose. The workflow is:



Write and evaluate a prompt relevant to your server's functionality

Define the prompt in your MCP server using the @mcp.prompt decorator

Clients can request the prompt at any time

Arguments provided by the client become keyword arguments in your prompt function

The function returns formatted messages ready for the AI model

This system creates reusable, parameterized prompts that maintain consistency while allowing customization through variables. It's particularly useful for complex workflows where you want to ensure the AI receives properly structured instructions every time.

