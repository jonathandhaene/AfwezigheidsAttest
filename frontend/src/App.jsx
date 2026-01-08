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
                      {/* Overall Status */}
                      <div className="mb-4 text-center">
                        <h4 className={`mb-2 ${result.valid ? 'text-success' : 'text-danger'}`}>
                          <span className={`badge ${result.valid ? 'bg-success' : 'bg-danger'} fs-5 px-4 py-2`}>
                            {result.valid ? '✓ GELDIG' : '✗ ONGELDIG'}
                          </span>
                        </h4>
                        {result.message && (
                          <div className={`alert ${result.valid ? 'alert-success' : 'alert-danger'} mt-3`} role="alert">
                            <div style={{ whiteSpace: 'pre-line' }}>
                              {result.message}
                            </div>
                          </div>
                        )}
                      </div>

                      {result.details && Object.keys(result.details).length > 0 && (
                        <div className="row g-3">
                          {/* File Information Section */}
                          {(result.details.Bestandsnaam || result.details['Verwerkt op']) && (
                            <div className="col-12">
                              <div className="card bg-light">
                                <div className="card-header bg-secondary text-white">
                                  <h6 className="mb-0">
                                    <i className="bi bi-file-earmark-text"></i> 📄 Bestandsinformatie
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      {result.details.Bestandsnaam && (
                                        <tr>
                                          <td className="fw-bold" style={{width: '40%'}}>Bestandsnaam:</td>
                                          <td>{result.details.Bestandsnaam}</td>
                                        </tr>
                                      )}
                                      {result.details['Verwerkt op'] && (
                                        <tr>
                                          <td className="fw-bold">Verwerkt op:</td>
                                          <td>{result.details['Verwerkt op']}</td>
                                        </tr>
                                      )}
                                      {result.details.Status && (
                                        <tr>
                                          <td className="fw-bold">Status:</td>
                                          <td>
                                            <span className={`badge ${result.valid ? 'bg-success' : 'bg-danger'}`}>
                                              {result.details.Status}
                                            </span>
                                          </td>
                                        </tr>
                                      )}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Patient Information Section */}
                          {result.details['Patiënt'] && (
                            <div className="col-12">
                              <div className="card bg-light">
                                <div className="card-header bg-info text-white">
                                  <h6 className="mb-0">
                                    <i className="bi bi-person"></i> 👤 Patiëntgegevens
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      {result.details['Patiënt'] && (
                                        <tr>
                                          <td className="fw-bold" style={{width: '40%'}}>Naam:</td>
                                          <td>{result.details['Patiënt']}</td>
                                        </tr>
                                      )}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Doctor Information Section */}
                          {(result.details.Arts || result.details['RIZIV Nummer']) && (
                            <div className="col-12">
                              <div className="card bg-light">
                                <div className="card-header bg-primary text-white">
                                  <h6 className="mb-0">
                                    <i className="bi bi-person-badge"></i> 🩺 Artsgegevens
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      {result.details.Arts && (
                                        <tr>
                                          <td className="fw-bold" style={{width: '40%'}}>Arts:</td>
                                          <td>{result.details.Arts}</td>
                                        </tr>
                                      )}
                                      {result.details['RIZIV Nummer'] && (
                                        <tr>
                                          <td className="fw-bold">RIZIV Nummer:</td>
                                          <td>
                                            <code className="text-primary">{result.details['RIZIV Nummer']}</code>
                                          </td>
                                        </tr>
                                      )}
                                      {result.details['Handtekening aanwezig'] && (
                                        <tr>
                                          <td className="fw-bold">Handtekening:</td>
                                          <td>
                                            <span className={`badge ${result.details['Handtekening aanwezig'] === 'Ja' ? 'bg-success' : 'bg-warning'}`}>
                                              {result.details['Handtekening aanwezig'] === 'Ja' ? '✓ Ja' : '✗ Nee'}
                                            </span>
                                          </td>
                                        </tr>
                                      )}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Incapacity Period Section */}
                          {(result.details['Onmogelijkheid vanaf'] || result.details['Onmogelijkheid tot']) && (
                            <div className="col-12">
                              <div className="card bg-light">
                                <div className="card-header bg-warning text-dark">
                                  <h6 className="mb-0">
                                    <i className="bi bi-calendar-range"></i> 📅 Periode van Onmogelijkheid
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      {result.details['Onmogelijkheid vanaf'] && (
                                        <tr>
                                          <td className="fw-bold" style={{width: '40%'}}>Van:</td>
                                          <td>{result.details['Onmogelijkheid vanaf']}</td>
                                        </tr>
                                      )}
                                      {result.details['Onmogelijkheid tot'] && (
                                        <tr>
                                          <td className="fw-bold">Tot:</td>
                                          <td>{result.details['Onmogelijkheid tot']}</td>
                                        </tr>
                                      )}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Summary Section */}
                          {result.details.Samenvatting && (
                            <div className="col-12">
                              <div className="card bg-light">
                                <div className="card-header bg-success text-white">
                                  <h6 className="mb-0">
                                    <i className="bi bi-file-text"></i> 📋 Samenvatting
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <p className="mb-0">{result.details.Samenvatting}</p>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Warnings Section */}
                          {result.details.Waarschuwingen && Array.isArray(result.details.Waarschuwingen) && result.details.Waarschuwingen.length > 0 && (
                            <div className="col-12">
                              <div className="alert alert-warning mb-0" role="alert">
                                <h6 className="alert-heading mb-2">⚠️ Waarschuwingen</h6>
                                <ul className="mb-0">
                                  {result.details.Waarschuwingen.map((warning, index) => (
                                    <li key={index}>{warning}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}

                          {/* Errors Section */}
                          {result.details.Fouten && Array.isArray(result.details.Fouten) && result.details.Fouten.length > 0 && (
                            <div className="col-12">
                              <div className="alert alert-danger mb-0" role="alert">
                                <h6 className="alert-heading mb-2">❌ Fouten</h6>
                                <ul className="mb-0">
                                  {result.details.Fouten.map((error, index) => (
                                    <li key={index}>{error}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}

                          {/* Other Details */}
                          {Object.entries(result.details)
                            .filter(([key]) => !['Bestandsnaam', 'Verwerkt op', 'Status', 'Patiënt', 'Arts', 'RIZIV Nummer', 
                                                  'Handtekening aanwezig', 'Onmogelijkheid vanaf', 'Onmogelijkheid tot', 
                                                  'Samenvatting', 'Waarschuwingen', 'Fouten', 'Reden', 'Aantal fouten'].includes(key))
                            .length > 0 && (
                            <div className="col-12">
                              <div className="card bg-light">
                                <div className="card-header bg-secondary text-white">
                                  <h6 className="mb-0">
                                    <i className="bi bi-info-circle"></i> ℹ️ Overige Informatie
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      {Object.entries(result.details)
                                        .filter(([key]) => !['Bestandsnaam', 'Verwerkt op', 'Status', 'Patiënt', 'Arts', 'RIZIV Nummer', 
                                                              'Handtekening aanwezig', 'Onmogelijkheid vanaf', 'Onmogelijkheid tot', 
                                                              'Samenvatting', 'Waarschuwingen', 'Fouten', 'Reden', 'Aantal fouten'].includes(key))
                                        .map(([key, value]) => (
                                          <tr key={key}>
                                            <td className="fw-bold" style={{width: '40%'}}>{key}:</td>
                                            <td>{typeof value === 'object' ? JSON.stringify(value) : value}</td>
                                          </tr>
                                        ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </div>
                          )}
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
