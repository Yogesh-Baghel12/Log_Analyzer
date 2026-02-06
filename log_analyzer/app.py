from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)

log_analysis_prompt_text="""
You are a senior site reliability engineer.
Analyze the following application logs.
1. Identify the main errors or failures.
2. Explain the likely root cause in simple terms.
3. Suggest practical next steps to fix or investigate.
4. Mention any suspicious patterns or repeated issues.
Logs:
{log_data}
Respond in clear paragraphs. Avoid jargon where possible.
"""


def split_logs(log_text:str):
    """Splits the log text into manageable chunks"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    return splitter.split_text(log_text)


def analyze_logs(log_text:str):
    """Analyzes logs by splitting and processing each chunk"""
    chunks = split_logs(log_text)
    combined_analysis = []
    
    for chunk in chunks:
        formatted_prompt = log_analysis_prompt_text.format(log_data=chunk)
        result=llm.invoke(formatted_prompt)
        combined_analysis.append(result.content)
        
    return "\n\n".join(combined_analysis)


@app.post("/analyze")
async def analyze_log_file(file: UploadFile = File(...)):
    """Analyze uploaded log file"""
    if not file.filename.endswith(".txt"):
        return JSONResponse(
            status_code=400,
            content={"error": "Only .txt log files are supported."}
        )
    
    try:
        content = await file.read()
        log_text = content.decode("utf-8", errors="ignore")
        if not log_text.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "Uploaded log file is empty."}
            )
        insights = analyze_logs(log_text)
        return {"analysis": insights}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"An error occurred while processing the log file: {str(e)}"}
        )


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)