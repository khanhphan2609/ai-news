# run_pipeline.sh
#!/bin/bash

echo "================================="
echo " AI NEWS RAG PIPELINE STARTING "
echo "================================="

# Activate virtual environment

# echo "Activating virtual environment..."
# source .venv/bin/activate

# Step 1: Crawl data

echo "---------------------------------"
echo "Step 1: Crawling WordPress data..."
python crawl_data.py

# Step 2: Preprocess NLP

echo "---------------------------------"
echo "Step 2: Preprocessing knowledge base..."
python preprocess_kb.py

# Step 3: Chunking + Indexing

echo "---------------------------------"
echo "Step 3: Chunking and creating inverted index..."
python chunking_indexing.py

# Step 4: Start API Server

echo "---------------------------------"
echo "Step 4: Starting API server..."
echo "Server running at http://localhost:3000"
python -m uvicorn api:app --port 3000 --reload
