import { FlatList, Pressable, Text, View } from 'react-native';
import { Link } from 'expo-router';

const ORDERS = [
  { id: 'WO-1042', site: 'Substation 7', due: '2026-10-08' },
  { id: 'WO-1043', site: 'Pump house B', due: '2026-10-09' },
];

export default function Index() {
  return (
    <View style={{ flex: 1, padding: 16 }}>
      <FlatList
        data={ORDERS}
        keyExtractor={(o) => o.id}
        renderItem={({ item }) => (
          <Link href={`/order/${item.id}`} asChild>
            <Pressable style={{ paddingVertical: 12 }}>
              <Text>{item.id}</Text>
              <Text>{item.site}</Text>
            </Pressable>
          </Link>
        )}
      />
    </View>
  );
}
