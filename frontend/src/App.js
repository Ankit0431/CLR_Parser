// import React, { useState } from "react";
// import axios from "axios";

// function App() {
//   const [grammar, setGrammar] = useState("");
//   const [result, setResult] = useState(null);
//   const [error, setError] = useState(null);

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     setError(null);
//     setResult(null);

//     try {
//       const response = await axios.post("http://127.0.0.1:5000/parse", {
//         grammar: grammar
//       });
//       setResult(response.data);
//     } catch (err) {
//       setError("Error parsing grammar. Please check input.");
//     }
//   };

//   return (
//     <div style={{ textAlign: "center", padding: "20px" }}>
//       <h2>CLR(1) Parser</h2>
//       <form onSubmit={handleSubmit}>
//         <textarea
//           rows="5"
//           cols="50"
//           value={grammar}
//           onChange={(e) => setGrammar(e.target.value)}
//           placeholder="Enter grammar rules..."
//         />
//         <br />
//         <button type="submit">Parse</button>
//       </form>

//       {error && <p style={{ color: "red" }}>{error}</p>}

//       {result && (
//         <div>
//           <h3>Parsing Results</h3>
//           <h4>States:</h4>
//           <pre>{JSON.stringify(result.states, null, 2)}</pre>

//           <h4>Action Table:</h4>
//           <pre>{JSON.stringify(result.action, null, 2)}</pre>

//           <h4>Goto Table:</h4>
//           <pre>{JSON.stringify(result.goto, null, 2)}</pre>
//         </div>
//       )}
//     </div>
//   );
// }

// export default App;
import React, { useState } from "react";
import axios from "axios";

// Helper component to display states
const StateDisplay = ({ states }) => {
  return (
    <div>
      {states.map((state, index) => (
        <div key={index} className="mb-4">
          <strong className="text-lg text-soft-gray">State {index}:</strong>
          <ul className="list-none pl-5">
            {state.map(([prodIndex, dotPos, lookahead]) => (
              <li key={`${prodIndex}-${dotPos}-${lookahead}`} className="text-sm text-soft-gray">
                [Production {prodIndex}, Dot: {dotPos}, Lookahead: {lookahead}]
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

// Helper component to display action table
const ActionTable = ({ action }) => {
  const entries = Object.entries(action);
  return (
    <table className="w-full border-collapse mt-2">
      <thead>
        <tr className="bg-dark-gray">
          <th className="border border-dark-gray p-2 text-soft-gray">State</th>
          <th className="border border-dark-gray p-2 text-soft-gray">Terminal</th>
          <th className="border border-dark-gray p-2 text-soft-gray">Action</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([[state, terminal], value], index) => (
          <tr key={index} className="hover:bg-dark-gray hover:bg-opacity-50 transition-colors">
            <td className="border border-dark-gray p-2 text-soft-gray">{state}</td>
            <td className="border border-dark-gray p-2 text-soft-gray">{terminal}</td>
            <td className="border border-dark-gray p-2 text-soft-gray">
              {Array.isArray(value) ? `${value[0]} ${value[1]}` : value}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

// Helper component to display goto table
const GotoTable = ({ goto }) => {
  const entries = Object.entries(goto);
  return (
    <table className="w-full border-collapse mt-2">
      <thead>
        <tr className="bg-dark-gray">
          <th className="border border-dark-gray p-2 text-soft-gray">State</th>
          <th className="border border-dark-gray p-2 text-soft-gray">Non-Terminal</th>
          <th className="border border-dark-gray p-2 text-soft-gray">Next State</th>
        </tr>
      </thead>
      <tbody>
        {entries.map(([[state, nonTerminal], nextState], index) => (
          <tr key={index} className="hover:bg-dark-gray hover:bg-opacity-50 transition-colors">
            <td className="border border-dark-gray p-2 text-soft-gray">{state}</td>
            <td className="border border-dark-gray p-2 text-soft-gray">{nonTerminal}</td>
            <td className="border border-dark-gray p-2 text-soft-gray">{nextState}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

function App() {
  const [grammar, setGrammar] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    try {
      const response = await axios.post("http://127.0.0.1:5000/parse", { grammar });
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.error || "Error connecting to the parser server.");
    }
  };

  return (
    <div className="min-h-screen w-full bg-black text-soft-gray p-5 flex justify-center">
      <div className="w-full max-w-2xl">
        <h2 className="text-3xl font-extrabold text-center mb-6 text-soft-gray drop-shadow-soft">
          CLR Parser
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            rows="5"
            value={grammar}
            onChange={(e) => setGrammar(e.target.value)}
            placeholder={`Enter grammar rules (one per line), e.g.:
E -> E + T
E -> T
T -> T * F
T -> F
F -> ( E )
F -> id`}
            className="w-full p-3 bg-black border border-dark-gray rounded-md font-mono text-sm text-soft-gray placeholder-soft-gray placeholder-opacity-50 focus:outline-none focus:ring-2 focus:ring-soft-blue transition-all"
          />
          <button
            type="submit"
            className="w-full py-2 px-4 bg-soft-blue text-black font-bold rounded-md hover:bg-dark-gray hover:text-soft-gray transition-all drop-shadow-soft"
          >
            Parse
          </button>
        </form>
        {error && (
          <p className="mt-4 text-error-red font-semibold text-center drop-shadow-soft">{error}</p>
        )}
        {result && !result.error && (
          <div className="mt-6 space-y-6">
            <h3 className="text-2xl font-semibold text-soft-gray drop-shadow-soft">
              Parsing Results
            </h3>
            <div className="bg-black p-4 rounded-md border border-dark-gray">
              <h4 className="text-lg font-medium mb-2 text-soft-gray">States:</h4>
              <StateDisplay states={result.states} />
            </div>
            <div className="bg-black p-4 rounded-md border border-dark-gray">
              <h4 className="text-lg font-medium mb-2 text-soft-gray">Action Table:</h4>
              <ActionTable action={result.action} />
            </div>
            <div className="bg-black p-4 rounded-md border border-dark-gray">
              <h4 className="text-lg font-medium mb-2 text-soft-gray">Goto Table:</h4>
              <GotoTable goto={result.goto} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;