import { StateProvider } from './context/GlobalState'
import ComparisonWorkspace from './components/ComparisonWorkspace'

function App() {
  return (
    <StateProvider>
      <ComparisonWorkspace />
    </StateProvider>
  )
}

export default App
