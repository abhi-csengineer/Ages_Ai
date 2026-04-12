import {
  Box, Flex, Text, Table, Thead, Tbody, Tr, Th, Td,
  TableContainer, Stat, StatNumber, StatLabel, Badge, HStack,
} from "@chakra-ui/react";
import { ModelComparisonRow } from "../types/contracts";

interface ModelComparisonMatrixProps {
  models: ModelComparisonRow[];
}

export function ModelComparisonMatrix({ models }: ModelComparisonMatrixProps) {
  return (
    <Box
      h="100%"
      bg="aegis.black"
      border="1px solid"
      borderColor="aegis.border"
      display="flex"
      flexDir="column"
      overflow="hidden"
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
        <Text fontSize="0.55rem" color="aegis.textDim" letterSpacing="0.15em">
          TILE-D // MULTI-MODEL COMPARISON MATRIX
        </Text>
        <Badge bg="aegis.limeDim" color="aegis.lime" fontSize="0.45rem" px={2}>
          JUDGE REQ A&B
        </Badge>
      </Flex>

      {/* Table */}
      <Box flex={1} overflow="auto" minH={0}>
        <TableContainer>
          <Table variant="unstyled" size="sm">
            <Thead>
              <Tr borderBottom="1px solid" borderColor="aegis.border">
                <Th color="aegis.textDim" borderColor="aegis.border" py={2}>MODEL</Th>
                <Th color="aegis.textDim" borderColor="aegis.border" py={2} textAlign="center">ACCURACY</Th>
                <Th color="aegis.textDim" borderColor="aegis.border" py={2} textAlign="center">DRIFT %</Th>
                <Th color="aegis.textDim" borderColor="aegis.border" py={2} textAlign="center">HUI-WALTER VIGOR</Th>
                <Th color="aegis.textDim" borderColor="aegis.border" py={2} textAlign="center">STATUS</Th>
              </Tr>
            </Thead>
            <Tbody>
              {models.map((row) => {
                const isCrit = row.accuracy < 0.90;
                const isDrift = row.driftPct > 10;
                const rowColor = row.isShadow
                  ? "aegis.lime"
                  : isCrit
                    ? "#FF0033"
                    : "aegis.text";

                return (
                  <Tr
                    key={row.model}
                    borderBottom="1px solid"
                    borderColor="aegis.border"
                    borderLeft={row.isShadow ? "3px solid" : "none"}
                    borderLeftColor={row.isShadow ? "aegis.lime" : "transparent"}
                    bg={row.isShadow ? "rgba(204,255,0,0.03)" : "transparent"}
                    _hover={{ bg: "rgba(204,255,0,0.05)" }}
                  >
                    {/* Model Name */}
                    <Td borderColor="aegis.border" py={3}>
                      <HStack spacing={2}>
                        <Text fontSize="0.7rem" color={rowColor} fontWeight={row.isShadow ? 700 : 400}>
                          {row.model}
                        </Text>
                        {row.isShadow && (
                          <Badge
                            bg="aegis.limeDim"
                            color="aegis.lime"
                            fontSize="0.4rem"
                            px={1.5}
                          >
                            SHADOW BENCHMARK
                          </Badge>
                        )}
                      </HStack>
                    </Td>

                    {/* Accuracy Stat */}
                    <Td borderColor="aegis.border" py={3}>
                      <Stat size="xs" textAlign="center">
                        <StatLabel>ACC</StatLabel>
                        <StatNumber
                          fontSize="md"
                          color={isCrit ? "#FF0033" : row.isShadow ? "aegis.lime" : "aegis.text"}
                        >
                          {row.accuracy.toFixed(4)}
                        </StatNumber>
                      </Stat>
                    </Td>

                    {/* Drift % Stat */}
                    <Td borderColor="aegis.border" py={3}>
                      <Stat size="xs" textAlign="center">
                        <StatLabel>DRIFT</StatLabel>
                        <StatNumber
                          fontSize="md"
                          color={isDrift ? "aegis.orange" : "aegis.lime"}
                        >
                          {row.driftPct.toFixed(1)}%
                        </StatNumber>
                      </Stat>
                    </Td>

                    {/* Vigor Stat */}
                    <Td borderColor="aegis.border" py={3}>
                      <Stat size="xs" textAlign="center">
                        <StatLabel>VIGOR</StatLabel>
                        <StatNumber
                          fontSize="md"
                          color={row.vigor < 0.90 ? "aegis.orange" : "aegis.lime"}
                        >
                          {row.vigor.toFixed(4)}
                        </StatNumber>
                      </Stat>
                    </Td>

                    {/* Status */}
                    <Td borderColor="aegis.border" py={3} textAlign="center">
                      <Badge
                        bg={isCrit ? "rgba(255,0,51,0.15)" : isDrift ? "aegis.orangeDim" : "aegis.limeDim"}
                        color={isCrit ? "#FF0033" : isDrift ? "aegis.orange" : "aegis.lime"}
                        fontSize="0.5rem"
                        px={2}
                        py={0.5}
                      >
                        {isCrit ? "▲ CRITICAL" : isDrift ? "⚠ DRIFTING" : "● NOMINAL"}
                      </Badge>
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
        </TableContainer>
      </Box>
    </Box>
  );
}
