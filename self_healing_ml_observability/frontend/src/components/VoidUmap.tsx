import { Box, Flex, HStack, Text } from "@chakra-ui/react";
import { motion, AnimatePresence } from "framer-motion";
import { EmbeddingPoint } from "../types/contracts";
import { StreamOrb } from "../hooks/useAegisStream";

interface VoidUmapProps {
  points: EmbeddingPoint[];
  mmdDrift: number;
  streamOrbs: StreamOrb[];
  pulseTick: number;
}

const MotionBox = motion(Box);

export function VoidUmap({ points, mmdDrift, streamOrbs, pulseTick }: VoidUmapProps) {
  return (
    <Box
      h="100%"
      bg="aegis.black"
      border="1px solid"
      borderColor="aegis.border"
      display="flex"
      flexDir="column"
      overflow="hidden"
      position="relative"
    >
      {/* Header */}
      <Flex
        px={3}
        py={1.5}
        borderBottom="1px solid"
        borderColor="aegis.border"
        justify="space-between"
        align="center"
        flexShrink={0}
      >
        <HStack spacing={2}>
          <Text fontSize="0.55rem" color="aegis.textDim" letterSpacing="0.15em">
            TILE-B // VOID UMAP 2D
          </Text>
        </HStack>
        <Text fontSize="0.5rem" color="aegis.lime" letterSpacing="0.1em">
          ◈ DRIFT: {mmdDrift.toFixed(4)}
        </Text>
      </Flex>

      {/* Canvas body */}
      <Box flex={1} position="relative" overflow="hidden" minH={0}>
        {/* Grid background */}
        <svg
          width="100%"
          height="100%"
          style={{ position: "absolute", inset: 0 }}
          viewBox="0 0 1000 1000"
          preserveAspectRatio="none"
        >
          <defs>
            <pattern id="umap-grid" width="50" height="50" patternUnits="userSpaceOnUse">
              <path d="M 50 0 L 0 0 0 50" fill="none" stroke="rgba(204,255,0,0.04)" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="1000" height="1000" fill="url(#umap-grid)" />

          {/* Crosshair */}
          <line x1="500" y1="0" x2="500" y2="1000" stroke="rgba(204,255,0,0.08)" strokeWidth="1" strokeDasharray="8,4" />
          <line x1="0" y1="500" x2="1000" y2="500" stroke="rgba(204,255,0,0.08)" strokeWidth="1" strokeDasharray="8,4" />

          {/* Reference points (dim lime) */}
          {points
            .filter((p) => p.source === "reference")
            .map((p) => (
              <circle
                key={p.request_id}
                cx={p.x * 1000}
                cy={p.y * 1000}
                r={2.5}
                fill="rgba(204,255,0,0.25)"
              />
            ))}

          {/* Live points (bright orange) */}
          {points
            .filter((p) => p.source === "live" && p.uncertainty < 0.6)
            .map((p) => (
              <circle
                key={p.request_id}
                cx={p.x * 1000}
                cy={p.y * 1000}
                r={3}
                fill="rgba(255,77,0,0.8)"
              />
            ))}

          {/* Attack outliers (red) */}
          {points
            .filter((p) => p.source === "live" && p.uncertainty >= 0.6)
            .map((p) => (
              <circle
                key={p.request_id}
                cx={p.x * 1000}
                cy={p.y * 1000}
                r={4}
                fill="#FF0033"
                opacity={0.9}
              />
            ))}
        </svg>

        {/* Stream orbs (framer-motion pulsing) */}
        <AnimatePresence>
          {streamOrbs.slice(-40).map((orb) => {
            const color =
              orb.status === "ATTACK"
                ? "#FF0033"
                : orb.status === "DRIFT"
                  ? "#FF4D00"
                  : "#CCFF00";
            return (
              <MotionBox
                key={orb.id}
                position="absolute"
                left={`${orb.x * 100}%`}
                top={`${orb.y * 100}%`}
                w="8px"
                h="8px"
                borderRadius="0 !important"
                bg={color}
                boxShadow={`0 0 12px ${color}, 0 0 24px ${color}`}
                initial={{ scale: 0, opacity: 1 }}
                animate={{ scale: [0, 1.5, 0.8], opacity: [0.8, 1, 0.3] }}
                exit={{ opacity: 0, scale: 0 }}
                transition={{ duration: 2.5, ease: "easeOut" }}
              />
            );
          })}
        </AnimatePresence>

        {/* Scanning sweep line (framer-motion) */}
        <MotionBox
          position="absolute"
          top={0}
          left={0}
          w="2px"
          h="100%"
          bg="aegis.lime"
          opacity={0.3}
          boxShadow="0 0 12px rgba(204,255,0,0.5)"
          key={`scan-${pulseTick}`}
          animate={{ x: ["0%", "100%"] }}
          transition={{ duration: 3, ease: "linear", repeat: Infinity }}
        />

        {/* Legend */}
        <HStack
          position="absolute"
          bottom={2}
          left={3}
          spacing={3}
        >
          <HStack spacing={1}>
            <Box w="6px" h="6px" bg="rgba(204,255,0,0.4)" />
            <Text fontSize="0.45rem" color="aegis.textDim">REF</Text>
          </HStack>
          <HStack spacing={1}>
            <Box w="6px" h="6px" bg="aegis.orange" />
            <Text fontSize="0.45rem" color="aegis.textDim">LIVE</Text>
          </HStack>
          <HStack spacing={1}>
            <Box w="6px" h="6px" bg="aegis.red" />
            <Text fontSize="0.45rem" color="aegis.textDim">ATTACK</Text>
          </HStack>
        </HStack>
      </Box>
    </Box>
  );
}
