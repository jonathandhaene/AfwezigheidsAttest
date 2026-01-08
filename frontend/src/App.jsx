import React, { useState } from 'react'
import './App.css'

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleFileChange = (event) => {
    const file = event.target.files[0]
    if (file) {
      setSelectedFile(file)
      setResult(null)
      setError(null)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Selecteer eerst een bestand')
      return
    }

    setUploading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch('/api/process-attestation', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`Fout bij verwerking: ${response.statusText}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      console.error('Upload error:', err)
      setError(err.message || 'Er is een fout opgetreden bij het uploaden van het bestand')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="App">
      <nav className="navbar navbar-dark bg-primary">
        <div className="container">
          <span className="navbar-brand mb-0 h1">Online Portaal</span>
        </div>
      </nav>

      <div className="container mt-5">
        <div className="row justify-content-center">
          <div className="col-md-8 col-lg-6">
            <div className="card shadow">
              <div className="card-body p-4">
                <h1 className="card-title text-center mb-4">Online Portaal</h1>
                
                <div className="alert alert-info" role="alert">
                  <h5 className="alert-heading">Welkom!</h5>
                  <p className="mb-0">
                    Upload uw <strong>afwezigheidsattest</strong> om het automatisch te laten 
                    verwerken en valideren door onze AI. Het systeem controleert de geldigheid 
                    van uw attest en geeft direct feedback.
                  </p>
                </div>

                <div className="mb-4">
                  <label htmlFor="fileInput" className="form-label fw-bold">
                    Selecteer uw afwezigheidsattest
                  </label>
                  <input
                    type="file"
                    className="form-control"
                    id="fileInput"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={handleFileChange}
                    disabled={uploading}
                  />
                  {selectedFile && (
                    <div className="mt-2 text-muted">
                      <small>Geselecteerd bestand: {selectedFile.name}</small>
                    </div>
                  )}
                </div>

                <button
                  className="btn btn-primary btn-lg w-100 mb-3"
                  onClick={handleUpload}
                  disabled={!selectedFile || uploading}
                >
                  {uploading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                      Verwerken...
                    </>
                  ) : (
                    'Upload en Valideer'
                  )}
                </button>

                {error && (
                  <div className="alert alert-danger" role="alert">
                    <strong>Fout:</strong> {error}
                  </div>
                )}

                {result && (
                  <div className={`card mt-4 ${result.valid ? 'border-success' : 'border-danger'}`}>
                    <div className={`card-header ${result.valid ? 'bg-success' : 'bg-danger'} text-white`}>
                      <h5 className="mb-0">
                        {result.valid ? '✓ Validatie Resultaat' : '✗ Validatie Resultaat'}
                      </h5>
                    </div>
                    <div className="card-body">
                      <div className="mb-3">
                        <strong>Status:</strong> 
                        <span className={`badge ms-2 ${result.valid ? 'bg-success' : 'bg-danger'}`}>
                          {result.valid ? 'Geldig' : 'Ongeldig'}
                        </span>
                      </div>
                      
                      {result.message && (
                        <div className="mb-3">
                          <strong>Bericht:</strong>
                          <div className="mt-1" style={{ whiteSpace: 'pre-line' }}>
                            {result.message}
                          </div>
                        </div>
                      )}
                      
                      {result.details && Object.keys(result.details).length > 0 && (
                        <div>
                          <strong>Details:</strong>
                          <ul className="mb-0 mt-1">
                            {Object.entries(result.details).map(([key, value]) => (
                              <li key={key}>
                                <strong>{key}:</strong> {value}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <footer className="text-center text-muted mt-5 mb-3">
        <small>© 2026 AfwezigheidsAttest Validatie Systeem</small>
      </footer>
    </div>
  )
}

export default App
