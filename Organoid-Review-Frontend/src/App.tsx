import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainMenu from './pages/MainMenu';
import SingleSetInterface from './pages/SingleSetInterface';


export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainMenu />} />
        <Route path="/dataset/:id" element={<SingleSetInterface />} />
      </Routes>
    </Router>
  );
}