# 🌾 Viksit Kisan (The AI Agri-Agent)

> **Team:** Viksit Kisan | **Event:** GenAI Hackathon Mumbai | **Track:** AgriTech  
> **Status:** 🟢 Live Prototype

<p align="left">
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Built%20with-Python%203.9+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://deepmind.google/technologies/gemini/">
    <img src="https://img.shields.io/badge/Powered%20by-Google%20Gemini%201.5-4285F4?style=flat-square&logo=google&logoColor=white" alt="Gemini">
  </a>
  <a href="https://cloud.google.com/run">
    <img src="https://img.shields.io/badge/Deployed%20on-Google%20Cloud%20Run-34A853?style=flat-square&logo=googlecloud&logoColor=white" alt="Cloud Run">
  </a>
</p>

---

## 📖 The Story of Ramdas
Ramdas, a cotton farmer in Yavatmal, lost his crop to a hailstorm. He had **72 hours** to file a claim under the *PM Fasal Bima Yojana*. He failed because he couldn't read the English/Hindi forms and didn't know his "Survey Number."

**Viksit Kisan** solves this. We built an AI Agent that listens to Ramdas, reads his land papers, and files the claim for him.

---

## 🚀 Key Features

### 🗣️ Dialect-Native Input
No typing required. The agent understands **Varhadi/Marathi** dialects directly. Just speak: *"Maza kapus gela"* (My cotton is gone).

### 👁️ Multimodal Intelligence
Uses **Gemini 1.5 Flash Vision** to analyze raw 7/12 Land Extracts (Satbara). It extracts critical data like `Survey Number` and `Owner Name` even from low-quality photos.

### 📝 Autonomous PDF Generation
**The Killer Feature:** We don't just give advice. We generate the **actual application form** in Marathi, ready for the bank. It uses advanced text shaping for correct Devanagari script and stamps the document with a "72-Hour Verification" seal.

---

## 🛠️ The Tech Stack (Google Arsenal)

| Component | Technology | Role |
| :--- | :--- | :--- |
| **The Brain** | **Google Gemini 1.5 Flash** | Multimodal reasoning (Audio + Image -> JSON). |
| **SDK** | **Google Gen AI SDK v2** | Interface for Gemini models. |
| **Frontend** | **Streamlit** | Mobile-responsive UI for Camera & Mic input. |
| **Deployment** | **Google Cloud Run** | Serverless hosting with HTTPS for mobile access. |
| **PDF Engine** | **fpdf2 + uharfbuzz** | Generates legally valid Marathi claim forms. |
| **Audio Output** | **gTTS** | Converts the Agent's reply back to Marathi Audio. |
| **Data** | **MongoDB Atlas** | Stores scheme rules and Mock User Profiles. |

---

## 🏗️ Architecture Flow

```mermaid
graph LR
    A[Farmer (Voice + Image)] --> B(Streamlit UI);
    B --> C{Gemini 1.5 Flash};
    C -- Extracts Data --> D[Agent Logic];
    D -- Fetches Profile --> E[(MongoDB Mock DB)];
    D -- Checks 72hr Rule --> F[Eligibility Engine];
    F --> G[PDF Generator];
    G --> H[Final Claim PDF];
    G --> I[Marathi Audio Confirmation];