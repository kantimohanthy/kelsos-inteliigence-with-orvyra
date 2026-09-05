import os
import uvicorn

if __name__ == "__main__":
    os.environ["ORVYRA_API_KEY"] = "test-secret-key-9999"
    uvicorn.run("main:app", host="127.0.0.1", port=8009, log_level="info")
