import tiktoken
from sentence_transformers import SentenceTransformer

class EmbeddingGenerator:
    def __init__(self):
        self.embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def chunk_text_by_tokens(self, text, chunk_size, encoding_name="cl100k_base"):
        """
        Splits the text into chunks based on the number of tokens.
        """
        encoding = tiktoken.get_encoding(encoding_name)
        tokens = encoding.encode(text)
        return [encoding.decode(tokens[i:i + chunk_size]) for i in range(0, len(tokens), chunk_size)]

    def generate_embeddings(self, chunks):
        """
        Generates embeddings for each chunk and returns a list of embeddings.
        """
        return [self.embedder.encode(chunk).tolist() for chunk in chunks]

    def process_text(self, text, chunk_size=1000):
        """
        Splits the text it into chunks, and generates the embeddings.
        """
        chunks = self.chunk_text_by_tokens(text, chunk_size)
        embeddings = self.generate_embeddings(chunks)
        return chunks, embeddings

# if __name__ == '__main__':
#     generator = EmbeddingGenerator()
#     chunks, embeddings = generator.process_text(text, chunk_size=800)
