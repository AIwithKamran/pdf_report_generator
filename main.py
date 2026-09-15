from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {
        "name" : "PDF Generator",
        "version": 'v1.1',
        'status' : 'running'
    }

# def main():
#     health()


# if __name__ == "__main__":
#     main()
