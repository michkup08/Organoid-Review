import ModelInterface from "./components/ModelInterface";


export default function App() {


  return (
    <div style={{ width: '100vw', height: '100vh', background: '#e8e8e8', display: 'flex', flexDirection: 'column' }}>
      <div style={{ 
        padding: '20px', 
        background: '#eee', 
        boxShadow: '0 -7px 10px rgba(0,0,0,0.1)',
        flexGrow: 1,
        borderRadius: '20px',
        margin: '10px',
      }}>
        <ModelInterface />
      </div>
    </div>
  );
}