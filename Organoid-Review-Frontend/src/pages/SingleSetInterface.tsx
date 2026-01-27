import { ArrowLeft} from "@mui/icons-material";
import ModelInterface from "../components/ModelInterface";
import { useNavigate, useParams } from "react-router-dom";
import { useOrganoid } from "../services/Organoid";

const SingleSetInterface = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const { data: organoidData, isLoading, error } = useOrganoid(+(id ?? 0));

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
            marginLeft: '80px'
          }}
        >
          Reprezentacja modelu 3D:
        </label>
        {isLoading ? (
          <div style={{marginLeft: '80px'}}>Ładowanie danych organoidu...</div>
        ) : error ? (
          <div style={{marginLeft: '80px'}}>Błąd: {error?.message}</div>
        ) : !organoidData?.isInitialized ? (
          <div style={{marginLeft: '80px'}}>Organoid nie został jeszcze zainicjalizowany.</div>
        ) : !organoidData?.isProcessedGlb ? (
          <div style={{marginLeft: '80px'}}>Model organoidu nie został jeszcze utworzony</div>
        ) : (
          <ModelInterface orgId={+(id ?? 0)} />
        )}
        
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
          padding: '5px', 
          background: '#eee',
          boxShadow: '0 0px 5px rgba(0,0,0,0.5)',
          opacity: 0.8,
          position: 'fixed',
          top: '20px',
          left: '20px',
          zIndex: 1000,
          borderRadius: '50%',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '50px',
          height: '50px'
        }}
        onClick={() => { navigate('/')}}
        >
        <ArrowLeft style={{ color: 'black', cursor: 'pointer', width: '40', height: '40'}}/>
      </div>
    </div>
  );
}

export default SingleSetInterface;