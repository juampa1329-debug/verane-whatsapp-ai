package com.verane.mobile.feature.customers

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.verane.mobile.core.network.CustomerDto

@Composable
fun CustomersScreen(
    viewModel: CustomersViewModel,
    modifier: Modifier = Modifier,
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val selected = state.selectedCustomer

    if (selected == null) {
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = state.search,
                    onValueChange = viewModel::updateSearch,
                    label = { Text("Buscar clientes") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = viewModel::refreshCustomers) {
                    Icon(Icons.Default.Refresh, contentDescription = "Recargar")
                }
            }

            if (state.loading) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                ) {
                    CircularProgressIndicator()
                }
            }
            if (state.error.isNotBlank()) {
                Text(state.error, color = MaterialTheme.colorScheme.error)
            }

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(state.customers, key = { it.phone }) { customer ->
                    CustomerItem(
                        customer = customer,
                        onClick = { viewModel.selectCustomer(customer.phone) },
                    )
                }
            }
        }
    } else {
        val form = state.form
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = viewModel::clearSelection) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Volver")
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "${selected.firstName} ${selected.lastName}".trim().ifBlank { selected.phone },
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(selected.phone, style = MaterialTheme.typography.bodySmall)
                }
                TextButton(onClick = viewModel::saveCustomer, enabled = !state.saving) {
                    Text(if (state.saving) "Guardando..." else "Guardar")
                }
            }

            HorizontalDivider()

            if (state.error.isNotBlank()) {
                Text(state.error, color = MaterialTheme.colorScheme.error)
            }
            if (state.success.isNotBlank()) {
                Text(state.success, color = MaterialTheme.colorScheme.primary)
            }

            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    OutlinedTextField(
                        value = form.firstName,
                        onValueChange = { value ->
                            viewModel.updateForm { it.copy(firstName = value) }
                        },
                        label = { Text("Nombre") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                item {
                    OutlinedTextField(
                        value = form.lastName,
                        onValueChange = { value ->
                            viewModel.updateForm { it.copy(lastName = value) }
                        },
                        label = { Text("Apellido") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                item {
                    OutlinedTextField(
                        value = form.city,
                        onValueChange = { value ->
                            viewModel.updateForm { it.copy(city = value) }
                        },
                        label = { Text("Ciudad") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                item {
                    OutlinedTextField(
                        value = form.customerType,
                        onValueChange = { value ->
                            viewModel.updateForm { it.copy(customerType = value) }
                        },
                        label = { Text("Tipo cliente") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                item {
                    OutlinedTextField(
                        value = form.interests,
                        onValueChange = { value ->
                            viewModel.updateForm { it.copy(interests = value) }
                        },
                        label = { Text("Intereses") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                item {
                    OutlinedTextField(
                        value = form.tags,
                        onValueChange = { value ->
                            viewModel.updateForm { it.copy(tags = value) }
                        },
                        label = { Text("Tags (comma-separated)") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                item {
                    OutlinedTextField(
                        value = form.paymentStatus,
                        onValueChange = { value ->
                            viewModel.updateForm { it.copy(paymentStatus = value) }
                        },
                        label = { Text("Estado de pago") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                item {
                    OutlinedTextField(
                        value = form.paymentReference,
                        onValueChange = { value ->
                            viewModel.updateForm { it.copy(paymentReference = value) }
                        },
                        label = { Text("Referencia de pago") },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                item {
                    OutlinedTextField(
                        value = form.notes,
                        onValueChange = { value ->
                            viewModel.updateForm { it.copy(notes = value) }
                        },
                        label = { Text("Notas") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 3,
                        maxLines = 8,
                    )
                }
            }
        }
    }
}

@Composable
private fun CustomerItem(
    customer: CustomerDto,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            val name = "${customer.firstName} ${customer.lastName}".trim().ifBlank { customer.phone }
            Text(name, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(customer.phone, style = MaterialTheme.typography.bodySmall)
            if (customer.lastText.isNotBlank()) {
                Text(
                    customer.lastText,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (customer.paymentStatus.isNotBlank()) {
                    Text("Pago: ${customer.paymentStatus}", style = MaterialTheme.typography.labelSmall)
                }
                if (customer.hasUnread) {
                    Text("Sin leer", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                }
            }
        }
    }
}
