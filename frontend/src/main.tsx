import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Transparent background for the body
document.body.style.backgroundColor = 'transparent';

ReactDOM.createRoot(document.getElementById('root')!).render(
    <App />
)
