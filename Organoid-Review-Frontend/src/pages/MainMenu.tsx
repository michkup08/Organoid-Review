import { useNavigate } from "react-router-dom";
import { useCreateOrganoid, useOrganoids } from "../services/Organoid";
import { useState, type ChangeEvent } from "react";
import './MailMenu.css';

const MainMenu = () => {
  const navigate = useNavigate();
  const { data: organoidsData, isLoading, error } = useOrganoids();
  const { mutate: createOrganoid, isPending: isUploading } = useCreateOrganoid();
  const [addExtracted, setAddExtracted] = useState(false);
  const [selectedTiffFile, setSelectedTiffFile] = useState<File | null>(null);
  const [newSetName, setNewSetName] = useState('');

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;

    if (!files || files.length === 0) {
      setSelectedTiffFile(null);
      return;
    }

    const file = files[0];
    
    if (file && (file.type === 'image/tiff' || file.name.match(/\.(tif|tiff)$/i))) {
      setSelectedTiffFile(file);
      console.log("Załadowano plik:", file);
    } else {
      alert("Proszę wybrać plik w formacie TIFF.");
      event.target.value = '';
    }
  };

  const handleAddDataset = async () => {

    if (selectedTiffFile && newSetName) {
      
      createOrganoid(
        { name: newSetName, file: selectedTiffFile }, 
        {
          onSuccess: () => {
            console.log("Dodano!");
            setNewSetName('');
            setSelectedTiffFile(null);
            setAddExtracted(false);
          },
          onError: (err) => {
            alert(err.message);
          }
        }
      );
    }
  };

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
          <div style={{ 
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
          onClick={() => setAddExtracted(true)}
          >
            {addExtracted ? 
            <div>
              <input 
                type="text" 
                style ={{
                  padding: '8px',
                  borderRadius: '8px',
                  border: '1px solid #ccc',
                  marginBottom: '10px',
                  width: '100%',
                  boxSizing: 'border-box'
                }}
                placeholder="Nazwa nowego zbioru"
                value={newSetName}
                onChange={(e) => setNewSetName(e.target.value)}
                />
              <input
                type="file"
                style={{
                  border: '1px solid #ccc',
                  borderRadius: '8px',
                  padding: '8px',
                  width: '100%',
                  boxSizing: 'border-box'
                }}
                accept=".tif, .tiff, image/tiff"
                onChange={handleFileChange}
                className="mb-4"
              />
              <button
                className="sendNewDatasetButton"
                disabled={!selectedTiffFile || !newSetName || isUploading}
                onClick={() => {
                  handleAddDataset();
                }}>
                {isUploading ? 'Twra przesyłanie skanów...':'Dodaj zbiór danych do eksperymentu'}
              </button>
            </div> :
            <div>
              <span>Dodaj</span>
              <span style={{color: '#999', fontSize: '0.9em'}}>+</span>
            </div>
            }
          </div>
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
      
      <div style={{ 
        padding: '25px', 
        background: '#eee', 
        boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
        borderRadius: '20px',
        flexGrow: 1
      }}>
        <label style={{ fontSize: '18px', fontWeight: 'bold', color: '#333' }}>
          Aktualny stan serwera:
        </label>
      </div>

    </div>
  );
}

export default MainMenu;