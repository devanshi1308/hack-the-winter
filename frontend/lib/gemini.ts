// Gemini API service using direct HTTP calls
const GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent';

interface GeminiResponse {
  candidates: Array<{
    content: {
      parts: Array<{
        text: string;
      }>;
    };
  }>;
  error?: {
    code: number;
    message: string;
    status: string;
  };
}

/**
 * Generate text using Gemini AI via direct API call
 * @param prompt - The prompt to send to Gemini
 * @returns Promise<string> - The generated text response
 */
export async function generateText(prompt: string): Promise<string> {
  try {
    const requestBody = {
      contents: [{
        parts: [{
          text: prompt
        }]
      }]
    };

    console.log('Making request to Gemini API...');

    const response = await fetch(`${GEMINI_API_URL}?key=${process.env.GEMINI_API_KEY}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    const data: GeminiResponse = await response.json();
    
    console.log('Gemini API response status:', response.status);
    console.log('Gemini API response data:', JSON.stringify(data, null, 2));

    if (!response.ok) {
      console.error('HTTP error:', response.status, response.statusText);
      console.error('Error data:', data);
      throw new Error(`HTTP error! status: ${response.status} - ${data.error?.message || 'Unknown error'}`);
    }

    if (data.error) {
      console.error('Gemini API error:', data.error);
      throw new Error(`Gemini API error: ${data.error.message}`);
    }

    return data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response generated';
  } catch (error) {
    console.error('Error generating text with Gemini:', error);
    throw new Error(`Failed to generate text: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Rewrite text using Gemini AI with a specific prompt for rewriting
 * @param originalText - The text to be rewritten
 * @param style - Optional style instructions (e.g., "formal", "casual", "professional")
 * @returns Promise<string> - The rewritten text
 */
export async function rewriteText(originalText: string, style?: string): Promise<string> {
  const styleInstruction = style ? ` in a ${style} style` : '';
  const prompt = `Please rewrite the following text to improve clarity, grammar, and flow${styleInstruction}. Keep the core meaning intact but make it more engaging and well-structured. the most important thing is to make the text more empathetic, more humane and more emotional, only respond in plain text. give one response, not multiple options. do not include any formatting. keep the response as concise as needed. respond only with the rewritten text and nothing more. do not include anything in the response besides the answer.

"${originalText}"

Rewritten text:`;

  return generateText(prompt);
}

/**
 * Generate a chat response using Gemini AI
 * @param message - The user's message
 * @param context - Optional context or conversation history
 * @returns Promise<string> - The AI's response
 */
export async function getChatResponse(message: string, context?: string): Promise<string> {
  const contextPrompt = context ? `Context: ${context}\n\n` : '';
  const prompt = `${contextPrompt}User: ${message}\n\nAssistant:`;
  
  return generateText(prompt);
}

/**
 * Generate content with custom instructions
 * @param content - The content to process
 * @param instructions - Specific instructions for how to process the content
 * @returns Promise<string> - The processed content
 */
export async function processWithInstructions(content: string, instructions: string): Promise<string> {
  const prompt = `${instructions}

Content to process:
"${content}"

Result:`;

  return generateText(prompt);
}
