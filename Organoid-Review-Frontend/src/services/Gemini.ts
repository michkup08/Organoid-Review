import { GoogleGenerativeAI } from "@google/generative-ai";
import { useMutation } from "@tanstack/react-query";

const API_KEY = import.meta.env.VITE_GEMINI_KEY;

const handleAskGemini = async (input: string) => {
      const genAI = new GoogleGenerativeAI(API_KEY);
      const model = genAI.getGenerativeModel({ model: "gemini-3-flash-preview" });

      const result = await model.generateContent(input);
      const text = result.response.text();
      
      return text;
  };

export const useGeminiResponse = (input: string) => {
    return useMutation({
        mutationFn: () => handleAskGemini(input),
        onSuccess: (data) => {
            console.log("Odpowiedź otrzymana:", data);
        },
        onError: (error) => {
            console.error("Błąd Gemini:", error);
        }
    })
}