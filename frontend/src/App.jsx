import React, { useState } from 'react'
import { useTranslation } from './i18n.jsx'
import './App.css'

function App() {
  const { t, language, setLanguage } = useTranslation()
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [progressStep, setProgressStep] = useState(0) // 0: idle, 1: uploading, 2: analyzing, 3: checking, 4: fraud check, 5: complete
  const [failedStep, setFailedStep] = useState(null) // Track which step failed
  const [processMessages, setProcessMessages] = useState([]) // Activity log messages
  const [isProcessCollapsed, setIsProcessCollapsed] = useState(false) // Collapse state for process steps

  const handleLanguageChange = (newLanguage) => {
    setLanguage(newLanguage)
    // Reset page state
    setSelectedFile(null)
    setUploading(false)
    setResult(null)
    setError(null)
    setProgressStep(0)
    setFailedStep(null)
    setProcessMessages([])
    setIsProcessCollapsed(false)
  }

  const addProcessMessage = (message) => {
    const timestamp = new Date().toLocaleTimeString(language === 'nl' ? 'nl-BE' : language === 'fr' ? 'fr-BE' : 'en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    setProcessMessages(prev => [{ text: message, time: timestamp }, ...prev])
  }

  const handleFileChange = (event) => {
    const file = event.target.files[0]
    if (file) {
      setSelectedFile(file)
      setResult(null)
      setError(null)
      setProgressStep(0)
      setFailedStep(null)
      setProcessMessages([])
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setError(t('upload.error'))
      return
    }

    setUploading(true)
    setError(null)
    setResult(null)
    setProgressStep(1) // Uploading
    setProcessMessages([])

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('language', language) // Send selected language to backend

      addProcessMessage(t('processStatus.fileSelected', { filename: selectedFile.name, size: (selectedFile.size / 1024).toFixed(2) }))
      addProcessMessage(t('processStatus.uploading'))
      
      // Start the API call - this will take a long time (includes upload + analysis + validation)
      const responsePromise = fetch('/api/process-attestation', {
        method: 'POST',
        body: formData
      })
      
      // Move to analysis step immediately while API call is in progress
      setProgressStep(2)
      addProcessMessage(t('processStatus.analyzingStart'))
      
      // Now wait for the response
      const response = await responsePromise

      if (!response.ok) {
        throw new Error(`${t('results.errorTitle')} ${response.statusText}`)
      }

      const data = await response.json()
      
      // Check if the API returned an error (service timeout, connection error, etc.)
      if (!data.valid && data.error_category) {
        // Service call failed (Azure AI timeout, database error, etc.)
        addProcessMessage(`❌ ${data.message}`)
        if (data.details) {
          const detailsStr = Object.entries(data.details)
            .map(([key, value]) => `${key}: ${value}`)
            .join(', ')
          addProcessMessage(`ℹ️ ${detailsStr}`)
        }
        
        // Stop at the step where failure occurred
        setProgressStep(2) // Show we reached analysis step
        setFailedStep(2) // Mark it as failed
        setError(data.message)
        setResult(data) // Still show the result card with error details
        return // Stop - don't continue to next steps
      }

      // API call succeeded - update progress through all steps with brief delays for visual feedback
      addProcessMessage(t('processStatus.analyzingComplete'))
      await new Promise(resolve => setTimeout(resolve, 300))
      
      setProgressStep(3)
      addProcessMessage(t('processStatus.validatingDoctor'))
      await new Promise(resolve => setTimeout(resolve, 300))
      
      setProgressStep(4)
      addProcessMessage(t('processStatus.validationComplete'))
      addProcessMessage(t('processStatus.fraudCheck'))
      await new Promise(resolve => setTimeout(resolve, 300))
      
      setProgressStep(5)
      addProcessMessage(t('processStatus.allChecksComplete'))
      
      setResult(data)
      
      if (data.valid) {
        addProcessMessage(t('processStatus.documentValid'))
      } else {
        addProcessMessage(t('processStatus.documentInvalid'))
      }
    } catch (err) {
      console.error('Upload error:', err)
      setError(err.message || t('upload.error'))
      setFailedStep(progressStep) // Mark current step as failed
      addProcessMessage(t('processStatus.error', { message: err.message || t('upload.error') }))
      // Don't reset progressStep so user can see where it failed
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="App">
      <nav className="navbar">
        <div className="container">
          <div className="d-flex justify-content-between align-items-center w-100">
            <span className="navbar-brand mb-0 h1">{t('app.title')}</span>
            {/* Language Switcher */}
            <div className="d-flex align-items-center gap-2">
              <label className="mb-0 me-2" style={{fontSize: '0.9rem'}}>{t('language.select')}</label>
              <select 
                value={language} 
                onChange={(e) => handleLanguageChange(e.target.value)}
                className="form-select form-select-sm"
                style={{width: 'auto'}}
              >
                <option value="nl">{t('language.nl')}</option>
                <option value="fr">{t('language.fr')}</option>
                <option value="en">{t('language.en')}</option>
              </select>
            </div>
          </div>
        </div>
      </nav>

      <div className="container mt-5">
        <div className="row justify-content-center">
          <div className="col-12" style={{maxWidth: '1200px'}}>
            <div className="card shadow">
              <div className="card-body p-4">
                <h1 className="card-title text-center mb-4">{t('app.title')}</h1>
                
                <div className="alert alert-info" role="alert">
                  <h5 className="alert-heading">{t('welcome.title')}</h5>
                  <p className="mb-0">
                    {t('welcome.description')}
                  </p>
                </div>

                <div className="mb-4">
                  <label htmlFor="fileInput" className="form-label fw-bold">
                    {t('upload.label')}
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
                      <small>{t('upload.selected', { filename: selectedFile.name })}</small>
                    </div>
                  )}
                </div>

                <div className="row justify-content-center">
                  <div className="col-lg-8 col-xl-6">
                    <button
                      className="btn btn-primary btn-lg w-100 mb-3"
                      onClick={handleUpload}
                      disabled={!selectedFile || uploading}
                    >
                      {uploading ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                          {t('upload.processing')}
                        </>
                      ) : (
                        t('upload.submitButton')
                      )}
                    </button>
                  </div>
                </div>

                {/* Progress Steps Indicator */}
                {progressStep > 0 && (
                  <div className="row justify-content-center mb-4">
                    <div className="col-lg-8 col-xl-6">
                      <div className="progress-container">
                    <div className="progress-steps">
                      {/* Step 1: Uploading */}
                      <div className={`progress-step ${progressStep >= 1 ? 'active' : ''} ${(progressStep > 1 || failedStep > 1) && failedStep !== 1 ? 'completed' : ''} ${failedStep === 1 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 1 ? '✕' : (progressStep > 1 || failedStep > 1) ? '✓' : '1'}
                        </div>
                        <div className="step-label">{t('steps.uploading')}</div>
                      </div>
                      
                      {/* Step 2: Analyzing */}
                      <div className={`progress-step ${progressStep >= 2 ? 'active' : ''} ${(progressStep > 2 || failedStep > 2) && failedStep !== 2 ? 'completed' : ''} ${failedStep === 2 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 2 ? '✕' : (progressStep > 2 || failedStep > 2) ? '✓' : '2'}
                        </div>
                        <div className="step-label">{t('steps.analyzing')}</div>
                      </div>
                      
                      {/* Step 3: Background Check */}
                      <div className={`progress-step ${progressStep >= 3 ? 'active' : ''} ${(progressStep > 3 || failedStep > 3) && failedStep !== 3 ? 'completed' : ''} ${failedStep === 3 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 3 ? '✕' : (progressStep > 3 || failedStep > 3) ? '✓' : '3'}
                        </div>
                        <div className="step-label">{t('steps.verification')}</div>
                      </div>
                      
                      {/* Step 4: Fraud Check */}
                      <div className={`progress-step ${progressStep >= 4 ? 'active' : ''} ${(progressStep > 4 || failedStep > 4) && failedStep !== 4 ? 'completed' : ''} ${failedStep === 4 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 4 ? '✕' : (progressStep > 4 || failedStep > 4) ? '✓' : '4'}
                        </div>
                        <div className="step-label">{t('steps.fraudCheck')}</div>
                      </div>
                      
                      {/* Step 5: Complete */}
                      <div className={`progress-step ${progressStep >= 5 ? 'active completed' : ''} ${failedStep === 5 ? 'failed' : ''}`}>
                        <div className="step-circle">
                          {failedStep === 5 ? '✕' : progressStep >= 5 ? '✓' : '5'}
                        </div>
                        <div className="step-label">{t('steps.result')}</div>
                      </div>
                    </div>
                    
                    {/* Animated Progress Bar - Only show while processing */}
                    {progressStep < 5 && (
                      <div className="progress-bar-container">
                        <div className={`progress-bar-fill ${failedStep ? 'failed' : ''}`} style={{ width: `${(progressStep / 5) * 100}%` }}></div>
                      </div>
                    )}

                    {/* Process Activity Log */}
                    {processMessages.length > 0 && (
                      <div className="process-log mt-3">
                        <div className="process-log-header d-flex justify-content-between align-items-center">
                          <small className="text-muted">{t('processStatus.title')}</small>
                          {progressStep >= 5 && (
                            <button
                              className="btn btn-link btn-sm text-decoration-none p-0"
                              onClick={() => setIsProcessCollapsed(!isProcessCollapsed)}
                              aria-expanded={!isProcessCollapsed}
                            >
                              <small>{isProcessCollapsed ? '▶ ' + t('processStatus.showDetails') : '▼ ' + t('processStatus.hideDetails')}</small>
                            </button>
                          )}
                        </div>
                        {(!isProcessCollapsed || progressStep < 5) && (
                          <div className="process-log-messages">
                            {processMessages.map((msg, index) => (
                              <div key={index} className="process-log-message">
                                <span className="process-log-time">{msg.time}</span>
                                <span className="process-log-text">{msg.text}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                      </div>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="alert alert-danger" role="alert">
                    <strong>{t('processStatus.error', {message: ''})}</strong> {error}
                  </div>
                )}

                {result && (
                  <div className={`card mt-4 ${result.valid ? 'border-success' : 'border-danger'}`}>
                    <div className={`card-header ${result.valid ? 'bg-success text-white' : 'bg-danger text-white'}`}>
                      <h5 className="mb-0 text-white">
                        {result.valid ? `✓ ${t('results.validTitle')}` : result.error_category ? `✗ ${t('results.errorTitle')}` : `✗ ${t('results.invalidTitle')}`}
                      </h5>
                    </div>
                    <div className="card-body">
                      {result.details && Object.keys(result.details).length > 0 && (
                        <div className="row g-3">
                          {/* Rejection Reason (shown at top when fraud detected) */}
                          {result.details.Reden && !result.details.Fouten && (
                            <div className="col-12">
                              <div className="alert alert-danger mb-0" role="alert">
                                <h6 className="alert-heading mb-2">🔒 {t('results.rejectionReason')}</h6>
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
                                <h6 className="alert-heading mb-2">❌ {t('results.validationErrors')}</h6>
                                <ul className="mb-0">
                                  {result.details.Fouten.map((error, index) => (
                                    <li key={index}>{error}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}

                          {/* Warnings Section */}
                          {result.details.Waarschuwingen && Array.isArray(result.details.Waarschuwingen) && result.details.Waarschuwingen.length > 0 && (
                            <div className="col-12">
                              <div className="alert alert-warning mb-0" role="alert">
                                <h6 className="alert-heading mb-2">⚠️ {t('results.warnings')}</h6>
                                <ul className="mb-0">
                                  {result.details.Waarschuwingen.map((warning, index) => (
                                    <li key={index}>{warning}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}

                          {/* File Information Section */}
                          {(result.details.Bestandsnaam || result.details['Verwerkt op']) && (
                            <div className="col-6">
                              <div className="card bg-light">
                                <div className="card-header border-bottom" style={{backgroundColor: '#b8c5d6'}}>
                                  <h6 className="mb-0 text-dark">
                                    📁 {t('results.generalInfo')}
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      {result.details['Zaak ID'] && (
                                        <tr>
                                          <td className="fw-bold" style={{width: '40%'}}>{t('results.fields.caseId')}:</td>
                                          <td>
                                            <span className="badge bg-warning text-dark">{result.details['Zaak ID']}</span>
                                          </td>
                                        </tr>
                                      )}
                                      {result.details.Bestandsnaam && (
                                        <tr>
                                          <td className="fw-bold">{t('results.fields.filename')}:</td>
                                          <td>{result.details.Bestandsnaam}</td>
                                        </tr>
                                      )}
                                      {result.details['Verwerkt op'] && (
                                        <tr>
                                          <td className="fw-bold">{t('results.fields.processedOn')}:</td>
                                          <td>{result.details['Verwerkt op']}</td>
                                        </tr>
                                      )}
                                      {result.details.Status && (
                                        <tr>
                                          <td className="fw-bold">{t('results.fields.status')}:</td>
                                          <td>
                                            <span className={`badge ${result.valid ? 'bg-success' : 'bg-danger'}`}>
                                              {result.details.Status === 'Goedgekeurd' ? t('results.fields.approved') : result.details.Status === 'Afgekeurd' ? t('results.fields.rejected') : result.details.Status}
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

                          {/* Summary and Other Details Section */}
                          {result.details.Samenvatting && (
                            <>
                              {/* Summary Section */}
                              <div className="col-md-6">
                                <div className="card bg-light">
                                  <div className="card-header border-bottom" style={{backgroundColor: '#b8cbb8'}}>
                                    <h6 className="mb-0 text-dark">
                                    <i className="bi bi-file-text"></i> 📋 {t('results.summary')}
                                    </h6>
                                  </div>
                                  <div className="card-body">
                                    <p className="mb-0">{result.details.Samenvatting}</p>
                                  </div>
                                </div>
                              </div>
                            </>
                          )}

                          {/* Patient Information Section */}
                          {result.details['Patiënt'] && (
                            <div className="col-md-6">
                              <div className="card bg-light">
                                <div className="card-header border-bottom" style={{backgroundColor: '#d4c5e0'}}>
                                  <h6 className="mb-0 text-dark">
                                    <i className="bi bi-person"></i> 👤 {t('results.patientInfo')}
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      <tr>
                                        <td className="fw-bold" style={{width: '40%'}}>{t('results.fields.name')}:</td>
                                        <td>{result.details['Patiënt'] || t('results.fields.notAvailable')}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">{t('results.fields.nationalNumber')}:</td>
                                        <td>
                                          {result.details['Rijksregisternummer'] ? (
                                            <code className="text-primary">{result.details['Rijksregisternummer']}</code>
                                          ) : (
                                            <span className="text-muted">{t('results.fields.notAvailable')}</span>
                                          )}
                                        </td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">{t('results.fields.birthdate')}:</td>
                                        <td>{result.details['Geboortedatum'] || <span className="text-muted">{t('results.fields.notAvailable')}</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">{t('results.fields.address')}:</td>
                                        <td>{result.details['Adres patiënt'] || <span className="text-muted">{t('results.fields.notAvailable')}</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">{t('results.fields.postalCode')}:</td>
                                        <td>{result.details['Postcode en gemeente patiënt'] || <span className="text-muted">{t('results.fields.notAvailable')}</span>}</td>
                                      </tr>
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Doctor Information Section */}
                          {(result.details.Arts || result.details['RIZIV Nummer']) && (
                            <div className="col-md-6">
                              <div className="card bg-light">
                                <div className="card-header border-bottom" style={{backgroundColor: '#a8c5d1'}}>
                                  <h6 className="mb-0 text-dark">
                                    <i className="bi bi-person-badge"></i> 🩺 {t('results.doctorInfo')}
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      <tr>
                                        <td className="fw-bold" style={{width: '40%'}}>{t('results.fields.name')}:</td>
                                        <td>{result.details.Arts || <span className="text-muted">{t('results.fields.notAvailable')}</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">{t('results.fields.rizivNumber')}:</td>
                                        <td>
                                          {result.details['RIZIV Nummer'] ? (
                                            <code className="text-primary">{result.details['RIZIV Nummer']}</code>
                                          ) : (
                                            <span className="text-muted">{t('results.fields.notAvailable')}</span>
                                          )}
                                        </td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">{t('results.fields.address')}:</td>
                                        <td>{result.details['Adres arts'] || <span className="text-muted">{t('results.fields.notAvailable')}</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">{t('results.fields.postalCode')}:</td>
                                        <td>{result.details['Postcode en gemeente arts'] || <span className="text-muted">{t('results.fields.notAvailable')}</span>}</td>
                                      </tr>
                                      <tr>
                                        <td className="fw-bold">{t('results.fields.phone')}:</td>
                                        <td>{result.details['Telefoonnummer arts'] || <span className="text-muted">{t('results.fields.notAvailable')}</span>}</td>
                                      </tr>
                                      {(result.details['Handtekening aanwezig'] || result.details['Handtekening']) && (
                                        <tr>
                                          <td className="fw-bold">{t('results.fields.signature')}:</td>
                                          <td>
                                            <span className={`badge ${(result.details['Handtekening aanwezig'] === 'Ja' || result.details['Handtekening'] === 'Ja') ? 'bg-success' : 'bg-warning'}`}>
                                              {(result.details['Handtekening aanwezig'] === 'Ja' || result.details['Handtekening'] === 'Ja') ? `✓ ${t('results.fields.yes')}` : `✗ ${t('results.fields.no')}`}
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
                            <div className="col-md-6">
                              <div className="card bg-light">
                                <div className="card-header border-bottom" style={{backgroundColor: '#e5d4b5'}}>
                                  <h6 className="mb-0 text-dark">
                                    <i className="bi bi-calendar-range"></i> 📅 {t('results.attestInfo')}
                                  </h6>
                                </div>
                                <div className="card-body">
                                  <table className="table table-sm table-borderless mb-0">
                                    <tbody>
                                      {result.details['Onmogelijkheid vanaf'] && (
                                        <tr>
                                          <td className="fw-bold" style={{width: '40%'}}>{t('results.fields.from')}:</td>
                                          <td>{result.details['Onmogelijkheid vanaf']}</td>
                                        </tr>
                                      )}
                                      {result.details['Onmogelijkheid tot'] && (
                                        <tr>
                                          <td className="fw-bold">{t('results.fields.to')}:</td>
                                          <td>{result.details['Onmogelijkheid tot']}</td>
                                        </tr>
                                      )}
                                      {result.details['Mag huis verlaten'] && (
                                        <tr>
                                          <td className="fw-bold">{t('results.fields.leaveHome')}:</td>
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
