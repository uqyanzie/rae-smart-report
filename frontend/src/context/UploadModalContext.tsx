import { createContext, useContext, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import UploadModal from '../components/UploadModal'
import type { components } from '../services/api'

type Transform = components['schemas']['TransformResponseDTO']

interface UploadModalContextType {
  openUploadModal: () => void
  closeUploadModal: () => void
  isUploadModalOpen: boolean
  lastCreatedBatchId: string | null
}

const UploadModalContext = createContext<UploadModalContextType | undefined>(undefined)

export function UploadModalProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const [lastCreatedBatchId, setLastCreatedBatchId] = useState<string | null>(null)
  const navigate = useNavigate()

  const openUploadModal = () => setIsOpen(true)
  const closeUploadModal = () => setIsOpen(false)

  const handleSuccess = (batchId: string, transform: Transform) => {
    setLastCreatedBatchId(batchId)
    // Navigate to batch detail page or stay on dashboard
    navigate(`/batches/${batchId}`, { state: { transform } })
  }

  return (
    <UploadModalContext.Provider
      value={{
        openUploadModal,
        closeUploadModal,
        isUploadModalOpen: isOpen,
        lastCreatedBatchId,
      }}
    >
      {children}
      <UploadModal isOpen={isOpen} onClose={closeUploadModal} onSuccess={handleSuccess} />
    </UploadModalContext.Provider>
  )
}

export function useUploadModal(): UploadModalContextType {
  const context = useContext(UploadModalContext)
  if (!context) {
    throw new Error('useUploadModal must be used within an UploadModalProvider')
  }
  return context
}
