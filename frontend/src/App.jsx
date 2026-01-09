import React, { useState } from 'react'
import './App.css'

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [progressStep, setProgressStep] = useState(0) // 0: idle, 1: uploading, 2: analyzing, 3: checking, 4: fraud check, 5: complete
  const [failedStep, setFailedStep] = useState(null) // Track which step failed

  const handleFileChange = (event) => {
    const file = event.target.files[0]
    if (file) {
      setSelectedFile(file)
      setResult(null)
      setError(null)
      setProgressStep(0)
      setFailedStep(null)
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
    setProgressStep(1) // Uploading

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      // Simulate upload step
      await new Promise(resolve => setTimeout(resolve, 800))
      setProgressStep(2) // Analyzing

      const response = await fetch('/api/process-attestation', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`Fout bij verwerking: ${response.statusText}`)
      }

      // Simulate analysis step
      await new Promise(resolve => setTimeout(resolve, 1000))
      setProgressStep(3) // Background check

      const data = await response.json()
      
      // Simulate background check step
      await new Promise(resolve => setTimeout(resolve, 800))
      setProgressStep(4) // Fraud case check
      
      // Simulate fraud case processing
      await new Promise(resolve => setTimeout(resolve, 600))
      setProgressStep(5) // Complete
      
      setResult(data)
    } catch (err) {
      console.error('Upload error:', err)
      setError(err.message || 'Er is een fout opgetreden bij het uploaden van het bestand')
      setFailedStep(progressStep) // Mark current step as failed
      // Don't reset progressStep so user can see where it failed
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

                {/* Progress Steps Indicator */}
                {progressStep > 0 && (
                  <div className="progress-container mb-4">
                    <div className="progress-steps">
                      {/* Step 1: Uploading */}
                      <div className={`progress-step ${progressStep >= 1 ? 'active' : ''} ${progressStep > 1 && failedStep !== 1 ? 'completed' : ''} ${failedStep === 1 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 1 ? '✕' : progressStep > 1 ? '✓' : '1'}
                        </div>
                        <div className="step-label">Uploaden</div>
                      </div>
                      
                      {/* Step 2: Analyzing */}
                      <div className={`progress-step ${progressStep >= 2 ? 'active' : ''} ${progressStep > 2 && failedStep !== 2 ? 'completed' : ''} ${failedStep === 2 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 2 ? '✕' : progressStep > 2 ? '✓' : '2'}
                        </div>
                        <div className="step-label">Analyseren</div>
                      </div>
                      
                      {/* Step 3: Background Check */}
                      <div className={`progress-step ${progressStep >= 3 ? 'active' : ''} ${progressStep > 3 && failedStep !== 3 ? 'completed' : ''} ${failedStep === 3 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 3 ? '✕' : progressStep > 3 ? '✓' : '3'}
                        </div>
                        <div className="step-label">Verificatie</div>
                      </div>
                      
                      {/* Step 4: Fraud Check */}
                      <div className={`progress-step ${progressStep >= 4 ? 'active' : ''} ${progressStep > 4 && failedStep !== 4 ? 'completed' : ''} ${failedStep === 4 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 4 ? '✕' : progressStep > 4 ? '✓' : '4'}
                        </div>
                        <div className="step-label">Fraudecheck</div>
                      </div>
                      
                      {/* Step 5: Complete */}
                      <div className={`progress-step ${progressStep >= 5 ? 'active completed' : ''} ${failedStep === 5 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 5 ? '✕' : progressStep >= 5 ? '✓' : '5'}
                        </div>
                        <div className="step-label">Resultaat</div>
                      </div>
                    </div>
                    
                    {/* Animated Progress Bar */}
                    <div className="progress-bar-container">
                      <div className={`progress-bar-fill ${failedStep ? 'failed' : ''}`} style={{ width: `${(progressStep / 5) * 100}%` }}></div>
                    </div>
                  </div>
                )}

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
                      {result.details && Object.keys(result.details).length > 0 && (
                        <div className="row g-3">
                          {/* Rejection Reason (shown at top when fraud detected) */}
                          {result.details.Reden && !result.details.Fouten && (
                            <div className="col-12">
                              <div className="alert alert-danger mb-0" role="alert">
                                <h6 className="alert-heading mb-2">🔒 Reden van afkeuring</h6>
                                <ul className="mb-0">
                                  {result.details.Reden.split('.').filter(item => item.trim()).map((item, index) => (
                                    <li key={index}>{item.trim()}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}

                          {/* Errors Section (Validation Errors - shown at top when validation fails) */}
                          {result.details.Fouten && Array.isArray(result.details.Fouten) && result.details.Fouten.length > 0 && (
                            <div className="col-12">
                              <div className="alert alert-danger mb-0" role="alert">
                                <h6 className="alert-heading mb-2">❌ Validatiefouten</h6>
                                <ul className="mb-0">
                                  {result.details.Fouten.map((error, index) => (
                                    <li key={index}>{error}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}

                          {/* File Information Section */}
                          {(result.details.Bestandsnaam || result.details['Verwerkt op']) && (
                            <div className="col-12">
                              <div className="card bg-light">
                                <div className="card-header bg-secondary text-white">
                                  <h6 className="mb-0">
                                    <i className="bi bi-info-circle"></i> ℹ️ Informatie
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      {result.details['Zaak ID'] && (
                                        <tr>
                                          <td className="fw-bold" style={{width: '40%'}}>Zaak ID:</td>
                                          <td>
                                            <span className="badge bg-warning text-dark">{result.details['Zaak ID']}</span>
                                          </td>
                                        </tr>
                                      )}
                                      {result.details.Bestandsnaam && (
                                        <tr>
                                          <td className="fw-bold">Bestandsnaam:</td>
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
                                      <tr>
                                        <td className="fw-bold" style={{width: '40%'}}>Naam:</td>
                                        <td>{result.details['Patiënt'] || 'Niet beschikbaar'}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">Rijksregisternummer:</td>
                                        <td>
                                          {result.details['Rijksregisternummer'] ? (
                                            <code className="text-primary">{result.details['Rijksregisternummer']}</code>
                                          ) : (
                                            <span className="text-muted">Niet beschikbaar</span>
                                          )}
                                        </td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">Geboortedatum:</td>
                                        <td>{result.details['Geboortedatum'] || <span className="text-muted">Niet beschikbaar</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">Adres:</td>
                                        <td>{result.details['Adres patiënt'] || <span className="text-muted">Niet beschikbaar</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">Postcode en gemeente:</td>
                                        <td>{result.details['Postcode en gemeente patiënt'] || <span className="text-muted">Niet beschikbaar</span>}</td>
                                      </tr>
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
                                      <tr>
                                        <td className="fw-bold" style={{width: '40%'}}>Naam:</td>
                                        <td>{result.details.Arts || <span className="text-muted">Niet beschikbaar</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">RIZIV Nummer:</td>
                                        <td>
                                          {result.details['RIZIV Nummer'] ? (
                                            <code className="text-primary">{result.details['RIZIV Nummer']}</code>
                                          ) : (
                                            <span className="text-muted">Niet beschikbaar</span>
                                          )}
                                        </td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">Adres:</td>
                                        <td>{result.details['Adres arts'] || <span className="text-muted">Niet beschikbaar</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">Postcode en gemeente:</td>
                                        <td>{result.details['Postcode en gemeente arts'] || <span className="text-muted">Niet beschikbaar</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">Telefoonnummer:</td>
                                        <td>{result.details['Telefoonnummer arts'] || <span className="text-muted">Niet beschikbaar</span>}</td>
                                      </tr>
                                      {(result.details['Handtekening aanwezig'] || result.details['Handtekening']) && (
                                        <tr>
                                          <td className="fw-bold">Handtekening:</td>
                                          <td>
                                            <span className={`badge ${(result.details['Handtekening aanwezig'] === 'Ja' || result.details['Handtekening'] === 'Ja') ? 'bg-success' : 'bg-warning'}`}>
                                              {(result.details['Handtekening aanwezig'] === 'Ja' || result.details['Handtekening'] === 'Ja') ? '✓ Ja' : '✗ Nee'}
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
                          {(result.details['Onmogelijkheid vanaf'] || result.details['Onmogelijkheid tot'] || result.details['Mag huis verlaten']) && (
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
                                      {result.details['Mag huis verlaten'] && (
                                        <tr>
                                          <td className="fw-bold">Mag huis verlaten:</td>
                                          <td>
                                            <span className={`badge ${result.details['Mag huis verlaten'] === 'Ja' ? 'bg-success' : 'bg-secondary'}`}>
                                              {result.details['Mag huis verlaten']}
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

                          {/* Reason for Rejection (Security/Fraud) */}
                          {/* Other Details */}
                          {Object.entries(result.details)
                            .filter(([key]) => !['Bestandsnaam', 'Verwerkt op', 'Status', 'Patiënt', 'Rijksregisternummer', 
                                                  'Geboortedatum', 'Adres patiënt', 'Postcode en gemeente patiënt',
                                                  'Arts', 'RIZIV Nummer', 'Adres arts', 'Postcode en gemeente arts', 
                                                  'Telefoonnummer arts', 'Handtekening aanwezig', 'Handtekening',
                                                  'Onmogelijkheid vanaf', 'Onmogelijkheid tot', 'Mag huis verlaten',
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
                                        .filter(([key]) => !['Bestandsnaam', 'Verwerkt op', 'Status', 'Patiënt', 'Rijksregisternummer',
                                                              'Geboortedatum', 'Adres patiënt', 'Postcode en gemeente patiënt',
                                                              'Arts', 'RIZIV Nummer', 'Adres arts', 'Postcode en gemeente arts',
                                                              'Telefoonnummer arts', 'Handtekening aanwezig', 'Handtekening',
                                                              'Onmogelijkheid vanaf', 'Onmogelijkheid tot', 'Mag huis verlaten',
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
