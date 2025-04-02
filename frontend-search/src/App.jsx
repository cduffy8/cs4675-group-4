import { useState } from "react";
import axios from "axios";
import "./styles.css"; // Import CSS for styling

export default function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [vectorModel, setVectorModel] = useState("all-MiniLM-L6-v2"); // Default model
  const [hasSearched, setHasSearched] = useState(false); // Track if search has been initiated

  const search = async () => {
    if (!query) return;
    setLoading(true);
    setHasSearched(true); // Mark that search has been initiated
    try {
      const response = await axios.get("http://localhost:8000/search", {
        params: {
          query: query,
          vector_model: vectorModel,
          top_k: 5,
        },
        headers: {
          "accept": "application/json",
          "Content-Type": "application/json",
        },
      });

      setResults(response.data.results); // Assuming response contains results array
    } catch (error) {
      console.error("Search failed", error);
      setResults([]);
    }
    setLoading(false);
  };

  // Helper function to truncate text to 100 characters
  const truncateText = (text, maxLength = 100) => {
    if (text.length > maxLength) {
      return text.slice(0, maxLength) + "...";
    }
    return text;
  };

  return (
    <div className="container">
      {/* Navbar */}
      <nav className="navbar">
        <h1>CS4675 Vector Search: Next.JS Docs</h1>
        <div className="nav-links">
          <a
            href="https://github.com/cduffy8/cs4675-group-4"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img src="/assets/github.png" alt="GitHub" />
          </a>
          <a
            href="https://nextjs.org/docs"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img src="/assets/nextjs.png" alt="Next.JS Docs" />
          </a>
        </div>
      </nav>

      {/* Search Box */}
      <div className="search-container">
        <input
          type="text"
          className="search-input"
          placeholder="Enter search query..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="model-select"
          value={vectorModel}
          onChange={(e) => setVectorModel(e.target.value)}
        >
          <option value="all-MiniLM-L6-v2">all-MiniLM-L6-v2</option>
          <option value="paraphrase-MiniLM-L6-v2">paraphrase-MiniLM-L6-v2</option>
          <option value="all-distilroberta-v1">all-distilroberta-v1</option>
        </select>
        <button onClick={search} className="search-button">
          Search
        </button>
      </div>

      {/* Results */}
      {hasSearched && (
        <div className="results">
          {loading && <p className="loading-text">Searching...</p>}
          {results.length === 0 && !loading && <p>No results found.</p>}
          <div className="results-list">
            {results.map((result) => (
              <div key={result.id} className="result-item">
                <h3>
                  <a href={result.url} target="_blank" rel="noopener noreferrer">
                    {result.title}
                  </a>
                </h3>
                <p>{truncateText(result.text)}</p>
                <p>Score: {result.score}</p>
                <button
                  onClick={() => navigator.clipboard.writeText(result.id)}
                  className="copy-button"
                >
                  Copy ID
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
