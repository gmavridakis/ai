import { Stack } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <Stack screenOptions={{ headerShown: true }}>
        <Stack.Screen name="index" options={{ title: 'Work orders' }} />
        <Stack.Screen name="order/[id]" options={{ title: 'Order' }} />
      </Stack>
    </GestureHandlerRootView>
  );
}
