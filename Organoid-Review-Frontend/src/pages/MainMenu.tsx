import { useNavigate } from "react-router-dom";
import { useOrganoids } from "../services/Organoid";

const MainMenu = () => {
  const navigate = useNavigate();
  const { data: organoidsData, isLoading, error } = useOrganoids();

  if (isLoading) return <div>Ładowanie organoidów...</div>;
  
  if (error) return <div>Błąd: {error.message}</div>;

  return (
    <div style={{ 
      width: '100vw', 
      minHeight: '100vh', 
      background: '#e8e8e8',
      padding: '20px',
      boxSizing: 'border-box',
      display: 'flex',
      flexDirection: 'column',
      gap: '15px'  
    }}>
      
      <div style={{ 
        padding: '25px', 
        background: '#eee', 
        boxShadow: '0 4px 15px rgba(0,0,0,0.1)', 
        borderRadius: '20px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '15px' 
      }}>
        
        <label style={{ fontSize: '18px', fontWeight: 'bold', color: '#333', marginBottom: '5px', gridColumn: '1 / -1' }}>
            Dostępne zbiory danych:
        </label>
        
        {organoidsData?.map((value, index) => (
          <div key={index} style={{ 
            background: '#fff', 
            padding: '15px 20px',
            borderRadius: '12px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.05)', 
            fontWeight: '500',
            cursor: 'pointer',
            boxSizing: 'border-box',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            transition: 'transform 0.2s, box-shadow 0.2s',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateX(5px)';
            e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateX(0)';
            e.currentTarget.style.boxShadow = '0 2px 4px rgba(173, 42, 42, 0.05)';
          }}
          onClick={() => navigate(`/dataset/${value.id}`)}
          >
            <span>{value.name}</span>
            <span style={{color: '#999', fontSize: '0.9em'}}>➔</span>
          </div>
        ))}
        
      </div>

      <div style={{ 
        padding: '25px', 
        background: '#eee', 
        boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
        borderRadius: '20px',
        flexGrow: 1
      }}>
        <label style={{ fontSize: '18px', fontWeight: 'bold', color: '#333' }}>
          Zamodelowane modele dyfuzji ciała organoidu:
        </label>
      </div>
      
    </div>
  );
}

export default MainMenu;