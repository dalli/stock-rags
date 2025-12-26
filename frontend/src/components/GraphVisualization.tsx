import React, { useEffect, useRef, useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { GraphVisualizationResponse, GraphNode, GraphRelationship } from '@/api/types'

// 노드 색상 정의
const NODE_COLORS: Record<string, string> = {
  Company: '#1976D2',      // Blue
  Industry: '#388E3C',     // Green
  Theme: '#F57C00',        // Orange
  TargetPrice: '#7B1FA2',  // Purple
  Opinion: '#C2185B',      // Pink
}

// 노드 크기 정의
const NODE_SIZES: Record<string, number> = {
  Company: 8,
  Industry: 6,
  Theme: 5,
  TargetPrice: 4,
  Opinion: 4,
}

interface GraphVisualizationProps {
  data: GraphVisualizationResponse
  loading?: boolean
  height?: number | string
}

interface SelectedItem {
  type: 'node' | 'relationship'
  data: GraphNode | GraphRelationship
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  data,
  loading = false,
  height = '600px',
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)
  const [selectedItem, setSelectedItem] = useState<SelectedItem | null>(null)
  const [openDialog, setOpenDialog] = useState(false)

  useEffect(() => {
    if (!containerRef.current || !data?.nodes || loading) return

    // Dynamically import force-graph
    import('force-graph').then((module: any) => {
      const ForceGraph = module.default as any
      // Prepare graph data
      const graphData = {
        nodes: data.nodes.map((node) => ({
          id: `${node.type}:${node.id}`,
          name: node.label,
          type: node.type,
          originalNode: node,
          color: NODE_COLORS[node.type] || '#999',
          val: NODE_SIZES[node.type] || 5,
        })),
        links: data.relationships.map((rel) => ({
          source: `${rel.source_type}:${rel.source_id}`,
          target: `${rel.target_type}:${rel.target_id}`,
          label: rel.relationship_type,
          originalRelationship: rel,
        })),
      }

      // Create Force Graph instance
      const graph = ForceGraph()(containerRef.current!)
        .graphData(graphData as any)
        .nodeLabel((d: any) => `${d.name} (${d.type})`)
        .nodeColor((d: any) => d.color)
        .nodeVal((d: any) => d.val)
        .linkLabel((d: any) => d.label)
        .linkColor(() => 'rgba(0,0,0,0.2)')
        .linkDirectionalArrowLength(4)
        .linkDirectionalArrowRelPos(1)
        .width(containerRef.current?.clientWidth || 800)
        .height(typeof height === 'string' ? parseInt(height) : height)
        .onNodeClick((node: any) => {
          setSelectedItem({
            type: 'node',
            data: node.originalNode,
          })
          setOpenDialog(true)
        })
        .onLinkClick((link: any) => {
          setSelectedItem({
            type: 'relationship',
            data: link.originalRelationship,
          })
          setOpenDialog(true)
        })

      graphRef.current = graph

      // Set initial camera position
      const distance = 300
      graph.cameraPosition(
        { x: 0, y: 0, z: distance },
        { x: 0, y: 0, z: 0 },
        3000
      )

      // Handle window resize
      const handleResize = () => {
        if (containerRef.current) {
          graph
            .width(containerRef.current.clientWidth)
            .height(typeof height === 'string' ? parseInt(height) : height)
        }
      }

      window.addEventListener('resize', handleResize)

      return () => {
        window.removeEventListener('resize', handleResize)
      }
    })
  }, [data, loading, height])

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setTimeout(() => setSelectedItem(null), 300)
  }

  return (
    <Box sx={{ display: 'flex', gap: 2, height }}>
      {/* 그래프 렌더링 영역 */}
      <Box
        ref={containerRef}
        sx={{
          flex: 1,
          border: '1px solid #ddd',
          borderRadius: 1,
          background: '#f5f5f5',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {loading && (
          <Box
            sx={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              zIndex: 100,
            }}
          >
            <CircularProgress />
          </Box>
        )}
      </Box>

      {/* 정보 패널 */}
      <Box
        sx={{
          width: 320,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        {/* 범례 */}
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
            범례
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <Box
                key={type}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                }}
              >
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor: color,
                  }}
                />
                <Typography variant="body2">{type}</Typography>
              </Box>
            ))}
          </Box>
        </Paper>

        {/* 통계 */}
        <Grid container spacing={1}>
          <Grid item xs={6}>
            <Card>
              <CardContent sx={{ py: 1.5 }}>
                <Typography color="textSecondary" variant="body2">
                  Nodes
                </Typography>
                <Typography variant="h6">{data.stats.node_count}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6}>
            <Card>
              <CardContent sx={{ py: 1.5 }}>
                <Typography color="textSecondary" variant="body2">
                  Relationships
                </Typography>
                <Typography variant="h6">{data.stats.relationship_count}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* 노드 타입별 통계 */}
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
            노드 타입
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {Object.entries(data.stats.node_types).map(([type, count]) => (
              <Box
                key={type}
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Typography variant="body2">{type}</Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {count}
                </Typography>
              </Box>
            ))}
          </Box>
        </Paper>

        {/* 안내 메시지 */}
        <Paper sx={{ p: 2, bgcolor: '#f0f4ff' }}>
          <Typography variant="body2" color="textSecondary">
            노드 또는 관계를 클릭하여 상세 정보를 확인합니다.
          </Typography>
        </Paper>
      </Box>

      {/* 상세 정보 다이얼로그 */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            {selectedItem?.type === 'node' ? '노드 상세 정보' : '관계 상세 정보'}
          </Typography>
          <IconButton onClick={handleCloseDialog} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {selectedItem && selectedItem.type === 'node' && (
            <NodeDetailsView node={selectedItem.data as GraphNode} />
          )}
          {selectedItem && selectedItem.type === 'relationship' && (
            <RelationshipDetailsView relationship={selectedItem.data as GraphRelationship} />
          )}
        </DialogContent>
      </Dialog>
    </Box>
  )
}

interface NodeDetailsViewProps {
  node: GraphNode
}

const NodeDetailsView: React.FC<NodeDetailsViewProps> = ({ node }) => (
  <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        이름
      </Typography>
      <Typography variant="body2">{node.label}</Typography>
    </Box>

    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        타입
      </Typography>
      <Box
        sx={{
          display: 'inline-block',
          px: 1.5,
          py: 0.5,
          borderRadius: 1,
          backgroundColor: NODE_COLORS[node.type] || '#999',
          color: 'white',
        }}
      >
        <Typography variant="body2">{node.type}</Typography>
      </Box>
    </Box>

    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        ID
      </Typography>
      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
        {node.id}
      </Typography>
    </Box>

    {node.properties && Object.keys(node.properties).length > 0 && (
      <Box>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          추가 정보
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>키</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>값</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(node.properties).map(([key, value]) => (
              <TableRow key={key}>
                <TableCell>{key}</TableCell>
                <TableCell>{String(value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    )}
  </Box>
)

interface RelationshipDetailsViewProps {
  relationship: GraphRelationship
}

const RelationshipDetailsView: React.FC<RelationshipDetailsViewProps> = ({ relationship }) => (
  <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        관계 타입
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {relationship.relationship_type}
      </Typography>
    </Box>

    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        소스 노드
      </Typography>
      <Box sx={{ pl: 2, borderLeft: `3px solid ${NODE_COLORS[relationship.source_type] || '#999'}` }}>
        <Typography variant="body2">
          <strong>{relationship.source_label}</strong>
        </Typography>
        <Typography variant="body2" color="textSecondary" sx={{ fontSize: '0.875rem' }}>
          {relationship.source_type}: {relationship.source_id}
        </Typography>
      </Box>
    </Box>

    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        타겟 노드
      </Typography>
      <Box sx={{ pl: 2, borderLeft: `3px solid ${NODE_COLORS[relationship.target_type] || '#999'}` }}>
        <Typography variant="body2">
          <strong>{relationship.target_label}</strong>
        </Typography>
        <Typography variant="body2" color="textSecondary" sx={{ fontSize: '0.875rem' }}>
          {relationship.target_type}: {relationship.target_id}
        </Typography>
      </Box>
    </Box>

    {relationship.properties && Object.keys(relationship.properties).length > 0 && (
      <Box>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          추가 정보
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600 }}>키</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>값</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(relationship.properties).map(([key, value]) => (
              <TableRow key={key}>
                <TableCell>{key}</TableCell>
                <TableCell>{String(value)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    )}
  </Box>
)
