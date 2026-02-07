import { useState } from 'react';
import { GoogleGenerativeAI } from "@google/generative-ai";

const API_KEY = import.meta.env.VITE_GEMINI_KEY;

const GeminiChat = () => {
  const [input, setInput] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const handleAskGemini = async () => {
    if (!input) return;
    
    setLoading(true);
    try {
      const genAI = new GoogleGenerativeAI(API_KEY);
      const model = genAI.getGenerativeModel({ model: "gemini-3-flash-preview" });

      const result = await model.generateContent(input);
      const text = result.response.text();
      
      setResponse(text);
    } catch (error) {
      console.error("Błąd API:", error);
      setResponse("Wystąpił błąd podczas łączenia z Gemini.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial' }}>
      <h3>Zapytaj Gemini</h3>
      <textarea 
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Wpisz swoje pytanie..."
        rows={4}
        style={{ width: '100%', marginBottom: '10px' }}
      />
      <button onClick={handleAskGemini} disabled={loading}>
        {loading ? 'Generowanie...' : 'Wyślij'}
      </button>
      
      {response && (
        <div style={{ marginTop: '20px', background: '#f0f0f0', padding: '10px' }}>
          <strong>Odpowiedź:</strong>
          <p>{response}</p>
        </div>
      )}
    </div>
  );
};

export default GeminiChat;