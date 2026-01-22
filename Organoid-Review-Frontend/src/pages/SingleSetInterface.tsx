import { X } from "@mui/icons-material";
import ModelInterface from "../components/ModelInterface";
import { useNavigate } from "react-router-dom";

const SingleSetInterface = () => {
  const navigate = useNavigate();

  return (
    <div style={{ width: '100%', minHeight: '100vh', background: '#e8e8e8', display: 'flex', flexDirection: 'column' }}>
      
      <div style={{ 
        padding: '20px', 
        background: '#eee', 
        boxShadow: '0 -7px 10px rgba(0,0,0,0.1)',
        flexGrow: 1,
        borderRadius: '20px',
        margin: '10px',
        minHeight: '600px',
        display: 'flex', 
        flexDirection: 'column'
      }}>
        <label
          style={{
            fontSize: '18px',
            fontWeight: 'bold',
            marginBottom: '10px',
          }}
        >
          Reprezentacja modelu 3D:
        </label>
        <ModelInterface />
        
      </div>
      <div
        style={{ 
          padding: '20px', 
          background: '#eee', 
          boxShadow: '0 -7px 10px rgba(0,0,0,0.1)',
          borderRadius: '20px',
          margin: '10px'
        }}
      >
        <label
          style={{
            fontSize: '18px',
            fontWeight: 'bold',
          }}
        >
          Zamodelowany model dyfuzji ciała organoidu (przekrój i rozkład w 3D):
        </label>
        <div style={{
          display: 'flex', 
          flexDirection: 'row',
          gap: '20px',
          marginTop: '10px'
          }}>
          <div style={{
            flexGrow: 1,
            maxWidth: '50%'
          }}>
            <img 
                src="/images/modelDyfuzjiPodgladSlice.png" 
                alt="Maski" 
                style={{ 
                  objectFit: 'contain', 
                  borderRadius: '20px',
                  width: '100%',
                  height: 'auto',
                }} 
              />
          </div>
          <div style={{ 
            flexGrow: 1,
            maxWidth: '50%'
          }}>
            <img 
                src="/images/modelDyfuzjiPodgladRozklad.png" 
                alt="Maski" 
                style={{ 
                  objectFit: 'contain', 
                  borderRadius: '20px',
                  width: '100%',
                  height: 'auto',
                }} 
              />
          </div>
      </div>
      </div>
      <div style={{ 
          padding: '25px', 
          background: 'red',
          display: 'absolute',
          top: '20px',
          left: '20px',
          zIndex: 1000,
        }}
        onClick={() => { () => { navigate('/')}}}
        >
        <X style={{ color: 'white', cursor: 'pointer'}}/>
      </div>
    </div>
  );
}

export default SingleSetInterface;